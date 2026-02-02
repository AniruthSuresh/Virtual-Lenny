from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    RemovalPolicy
)

"""
Basically : 

1. users connect via WebSocket
2.messages go to a Lambda
3.Lambda runs your RAG agent
4. RAG agent calls Bedrock (LLM)
5. responses are streamed back to the same WebSocket connection
"""

class WebSocketStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # 1. DynamoDB to track who is online
        table = dynamodb.Table(self, "ConnTable",
            partition_key={"name": "connectionId", "type": dynamodb.AttributeType.STRING},
            removal_policy=RemovalPolicy.DESTROY
        )

        # 2. The RAG Agent (Docker Image)
        message_handler = _lambda.DockerImageFunction(self, "MessageHandler",
            code=_lambda.DockerImageCode.from_image_asset("../agent/message_handler"),
            timeout=Duration.minutes(5),
            memory_size=3008,
            environment={
                "QDRANT_URL": "your-url",
                "QDRANT_API_KEY": "your-key",
                "CONNECTIONS_TABLE": table.table_name
            }
        )

        # 3. POWER BLOCK: Grant access to Bedrock 
        message_handler.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModelWithResponseStream", # For the actual RAG stream
                "aws-marketplace:Subscribe",              # For the first-time auto-subscription
                "aws-marketplace:ViewSubscriptions"       # To verify access
            ],
            resources=["*"]
        ))

        # 4. Create the WebSocket API
        web_socket_api = apigwv2.WebSocketApi(self, "LennyWS")
        
        # Add a $default route for chat messages
        web_socket_api.add_route("$default",
            integration=integrations.WebSocketLambdaIntegration("MsgInteg", message_handler)
        )

        # 5. Grant permission to send messages BACK to the user
        message_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["execute-api:ManageConnections"],
            resources=["*"]
        ))