import json
import boto3
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# Warm-start: Loaded once when the container starts
MODEL_PATH = "/var/task/mxbai_model"
model = SentenceTransformer(MODEL_PATH, device="cpu")

"""
NOTE : Don't load the model inside the lamdba function -- once per container
and not once for every request
"""
# model = SentenceTransformer(
#     "mixedbread-ai/mxbai-embed-large-v1",
#     device="cuda"
# )


bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

qdrant = QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY'] , port=None) # because : https://github.com/qdrant/qdrant-client/issues/394#issuecomment-2075283788

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']

    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    apigw = boto3.client('apigatewaymanagementapi', endpoint_url=f"https://{domain}/{stage}" , region_name='us-east-1')

    try:
        # 1. Parse User Query
        body = json.loads(event.get('body', '{}'))
        user_query = body.get('message', '')

        # 2. RAG: Embedding
        query_vector = model.encode(user_query).tolist()

        search_result = qdrant.query_points(
            collection_name="virtual-lenny",
            query=query_vector,
            limit=3,
            timeout=10
        )
        results = search_result.points # https://github.com/qdrant/qdrant-client
        context_text = "\n\n".join([r.payload['content'] for r in results])

        # 3. Prompt Reconstruction 
        # prompt = f"""You are Lenny Rachitsky. Use the context below to answer.
        # Context: {context_text}
        # Question: {user_query}
        # Answer:"""

        prompt = f"""
        You are Lenny Rachitsky, a thoughtful startup advisor and writer.

        Answer the user's question using ONLY the context provided below.
        Do not add facts, examples, or opinions that are not grounded in the context.
        If the context is insufficient to answer clearly, say that directly.

        Guidelines:
        - Be concise but insightful
        - Use clear, simple language
        - Prefer practical advice over theory
        - Write in a calm, reflective tone
        - Do NOT mention that you were given context
        - Do NOT reference documents, posts, or sources explicitly

        Context:
        {context_text}

        Question:
        {user_query}

        Answer:
        """


        # https://docs.aws.amazon.com/code-library/latest/ug/python_3_bedrock-runtime_code_examples.html 
        # 4. Bedrock Streaming 
        response = bedrock.converse_stream(
                    modelId="amazon.nova-lite-v1:0",
                    messages=[{
                        "role": "user",
                        "content": [{"text": prompt}]
                    }],
                    inferenceConfig={"maxTokens": 512, "temperature": 0.5}
                )


        # 5. Token Streaming Loop for ConverseStream

        print("\n LENNY IS SPEAKING: ")
        for event in response.get("stream"):
            if "contentBlockDelta" in event:
                token = event["contentBlockDelta"]["delta"]["text"]
    
                # print(token, end="", flush=True) 
                try:
                    apigw.post_to_connection(
                        ConnectionId=connection_id, 
                        Data=json.dumps({"type": "chunk", "content": token})
                    )
                except:
                    pass

        apigw.post_to_connection(ConnectionId=connection_id, Data=json.dumps({"type": "done"}))

    except Exception as e:
        print(f"Error: {str(e)}")
        apigw.post_to_connection(ConnectionId=connection_id, Data=json.dumps({"type": "error", "message": str(e)}))

    return {'statusCode': 200}