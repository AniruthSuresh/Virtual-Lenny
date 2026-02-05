import json
import boto3
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from evaluator import RAGEvaluator

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

evaluator = RAGEvaluator()

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

qdrant = QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY'] , port=None) # because : https://github.com/qdrant/qdrant-client/issues/394#issuecomment-2075283788

def send_message(apigw_client, connection_id, payload):
    """
    Sends a JSON payload to a specific WebSocket connection.
    """
    try:
        apigw_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(payload)
        )
    except apigw_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone.")
    except Exception as e:
        print(f"Error sending message: {e}")


def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']

    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    apigw = boto3.client('apigatewaymanagementapi', endpoint_url=f"https://{domain}/{stage}" , region_name=os.environ['AWS_REGION'])

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
            timeout=10 , 
            with_payload=True,
            score_threshold=0.3
        )
        # results = search_result.points # https://github.com/qdrant/qdrant-client
        # context_text = "\n\n".join([r.payload['content'] for r in results])

        retrieval_metrics = evaluator.calculate_retrieval_score(search_result)
        print(f"📊 Retrieval avg score: {retrieval_metrics['avg_score']}")
        
        # Build context
        context_chunks = [r.payload['content'] for r in search_result]
        context_text = "\n\n---\n\n".join([
            f"[Source {i+1} - {r.payload.get('source', 'unknown')}]\n{content}"
            for i, (r, content) in enumerate(zip(search_result, context_chunks))
        ])

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

        full_response = ""
        
        response = bedrock.converse_stream(
            modelId="amazon.nova-lite-v1:0",
            messages=[{
                "role": "user",
                "content": [{"text": prompt}]
            }],
            inferenceConfig={
                "maxTokens": 512,
                "temperature": 0.7
            }
        )
        



        # https://docs.aws.amazon.com/code-library/latest/ug/python_3_bedrock-runtime_code_examples.html 
        # 4. Bedrock Streaming 
        # response = bedrock.converse_stream(
        #             modelId="amazon.nova-lite-v1:0",
        #             messages=[{
        #                 "role": "user",
        #                 "content": [{"text": prompt}]
        #             }],
        #             inferenceConfig={"maxTokens": 512, "temperature": 0.5}
        #         )


        # 5. Token Streaming Loop for ConverseStream

        # print("\n LENNY IS SPEAKING: ")
        # for event in response.get("stream"):
        #     if "contentBlockDelta" in event:
        #         token = event["contentBlockDelta"]["delta"]["text"]
    
        #         # print(token, end="", flush=True) 
        #         try:
        #             apigw.post_to_connection(
        #                 ConnectionId=connection_id, 
        #                 Data=json.dumps({"type": "chunk", "content": token})
        #             )
        #         except:
        #             pass

        for event_chunk in response.get("stream", []):
            if "contentBlockDelta" in event_chunk:
                token = event_chunk["contentBlockDelta"]["delta"]["text"]
                full_response += token
                
                send_message(apigw, connection_id, {
                    "type": "chunk",
                    "content": token
                })
        
        print("✅ Response generated")
        
        # Calculate evaluation scores
        groundedness = evaluator.calculate_groundedness_score(
            full_response, 
            context_chunks
        )
        
        coherence = evaluator.calculate_coherence_score(full_response)
        
        source_attribution = evaluator.calculate_source_attribution_score(
            full_response,
            search_result
        )
        
        print(f"📊 Groundedness: {groundedness}, Coherence: {coherence}, Attribution: {source_attribution}")
        
        # Calculate RAG score
        rag_score = evaluator.calculate_rag_score(
            retrieval_metrics,
            groundedness,
            coherence,
            source_attribution
        )
        
        print(f"🎯 RAG Score: {rag_score['overall']}% ({rag_score['grade']})")
        
        # Send evaluation scores
        send_message(apigw, connection_id, {
            "type": "evaluation",
            "score": rag_score
        })
        
        send_message(apigw, connection_id, {"type": "done"})
        
        return {'statusCode': 200}

    except Exception as e:
        print(f"Error: {str(e)}")
        apigw.post_to_connection(ConnectionId=connection_id, Data=json.dumps({"type": "error", "message": str(e)}))

    return {'statusCode': 200}