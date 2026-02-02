from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


class WebSocketStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
    
        root_dir = Path(__file__).resolve().parent.parent.parent
        agent_dir = root_dir / "agent"
        
        QDRANT_URL = os.getenv("QDRANT_URL")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

        # -------------------------
        # DynamoDB Table for Connection Tracking
        # -------------------------
        connections_table = dynamodb.Table(
            self, "ConnectionsTable",
            partition_key=dynamodb.Attribute(
                name="connectionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            table_name="virtual-lenny-connections"
        )

        # -------------------------
        # Lambda: Connect Handler
        # -------------------------
        connect_handler = _lambda.Function(
            self, "ConnectHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset(str(agent_dir / "connect_handler")),
            timeout=Duration.seconds(30),
            environment={
                "CONNECTIONS_TABLE": connections_table.table_name
            }
        )
        connections_table.grant_write_data(connect_handler)

        
        # -------------------------
        # Lambda: Disconnect Handler
        # -------------------------
        disconnect_handler = _lambda.Function(
            self, "DisconnectHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset(str(agent_dir / "disconnect_handler")),
            timeout=Duration.seconds(30),
            environment={
                "CONNECTIONS_TABLE": connections_table.table_name
            }
        )
        connections_table.grant_write_data(disconnect_handler)

        
        # -------------------------
        # Lambda: Message Handler (RAG Agent) - Docker
        # -------------------------
        message_handler = _lambda.DockerImageFunction(
            self, "MessageHandler",
            code=_lambda.DockerImageCode.from_image_asset(
                str(agent_dir / "message_handler")
            ),
            timeout=Duration.minutes(2),
            memory_size=3008,
            environment={
                "QDRANT_URL": QDRANT_URL,
                "QDRANT_API_KEY": QDRANT_API_KEY,
            }
        )
        
        # Grant Bedrock permissions
        message_handler.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ConverseStream",
                "bedrock:Converse"
            ],
            resources=["*"]  # You can restrict this to specific model ARNs
        ))
        
        # -------------------------
        # WebSocket API
        # -------------------------
        web_socket_api = apigwv2.WebSocketApi( # this creates the websocket server 
            self, "VirtualLennyWebSocket",

            # Browser opens WebSocket
            # → $connect
            # → ConnectHandler
            # → DynamoDB store connectionId
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration",
                    connect_handler
                )
            ),

            # Browser closes
            # → $disconnect
            # → DisconnectHandler
            # → DynamoDB cleanup
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration",
                    disconnect_handler
                )
            ),

            # Browser sends message
            # → $default
            # → MessageHandler
            # → RAG + Bedrock
            # → post_to_connection()
            default_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "MessageIntegration",
                    message_handler
                )
            )
        )
        
        # Deploy stage
        stage = apigwv2.WebSocketStage(
            self, "ProductionStage",
            web_socket_api=web_socket_api,
            stage_name="prod",
            auto_deploy=True
        )
    


        # message_handler Lambda permission to send messages back to connected WebSocket clients. 
        web_socket_api.grant_manage_connections(message_handler)
        
        # -------------------------
        # Outputs
        # -------------------------
        CfnOutput(
            self, "WebSocketURL",
            value=stage.url,
            description="WebSocket API endpoint for Virtual Lenny chat",
            export_name="VirtualLennyWebSocketURL"
        )
        
        CfnOutput(
            self, "WebSocketApiId",
            value=web_socket_api.api_id,
            description="WebSocket API ID"
        )

