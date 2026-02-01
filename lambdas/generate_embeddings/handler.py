import os
import json
import boto3
import torch
import io
from sentence_transformers import SentenceTransformer

s3 = boto3.client('s3')

MODEL_NAME = "mixedbread-ai/mxbai-embed-large-v1" # this was the best model for us in terms of performance vs cost
model = SentenceTransformer(MODEL_NAME, device="cuda") if torch.cuda.is_available() else SentenceTransformer(MODEL_NAME, device="cpu")

def lambda_handler(event, context):
    """
    Input: {
        "bucket": "virtual-lenny-bucket",
        "input_key": "data/chunks/final_chunks.json",
        "output_key": "data/embedded/mxbai_corpus.pt"
    }
    """
    bucket = event['bucket']
    input_key = event['input_key']
    output_key = event['output_key']

    try:
        # 1. Download chunks from S3
        print(f"Downloading chunks from s3://{bucket}/{input_key}")
        obj = s3.get_object(Bucket=bucket, Key=input_key)
        all_chunks = json.loads(obj['Body'].read().decode('utf-8'))
        
        # 2. Extract text for embedding
        # Your logic: [c['content'] for c in all_chunks]
        corpus_texts = [c.get('content') or c.get('text', '') for c in all_chunks]
        
        print(f"Generating embeddings for {len(corpus_texts)} chunks...")
        corpus_embs = model.encode(
            corpus_texts, 
            convert_to_tensor=True, 
            show_progress_bar=True
        )
        
        # 3. Save to a buffer (In-memory file)
        buffer = io.BytesIO()
        torch.save({"embeddings": corpus_embs, "chunks": all_chunks}, buffer)
        buffer.seek(0)
        
        # 4. Upload .pt file to S3
        print(f"Uploading embeddings to s3://{bucket}/{output_key}")
        s3.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=buffer.getvalue(),
            ContentType='application/octet-stream'
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "embedding_shape": list(corpus_embs.shape),
                "output_key": output_key
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}