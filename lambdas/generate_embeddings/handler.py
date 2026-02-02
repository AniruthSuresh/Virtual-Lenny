import os
import json
import boto3
import torch
import io
import botocore
import numpy as np
from sentence_transformers import SentenceTransformer

s3 = boto3.client('s3')

# MLOps Optimization: Point to baked-in model and set cache to writable /tmp
os.environ['TRANSFORMERS_CACHE'] = '/tmp'
os.environ['HF_HOME'] = '/tmp'
MODEL_PATH = "/var/task/mxbai_model"

# Load model globally for warm-start performance
model = SentenceTransformer(MODEL_PATH, device="cpu", local_files_only=True)

def lambda_handler(event, context):
    """
    AWS Lambda handler to generate sentence embeddings using NumPy for storage.
    
    Input: {
        "bucket": "virtual-lenny-bucket",
        "input_key": "data/chunks/final_chunks.json",
        "output_key": "data/embedded/mxbai_corpus.npz"
    }
    """
    bucket = event['bucket']
    input_key = event['input_key']
    output_key = event['output_key'] 

    try:
        s3.head_object(Bucket=bucket, Key=output_key)
        print(f" SKIPPING: File already exists at s3://{bucket}/{output_key}")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "skipped", 
                "message": "File already exists",
                "output_key": output_key
            })
        }
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] != "404":
            raise e

    try:
        # 2. Download chunks from S3
        print(f"Downloading chunks from s3://{bucket}/{input_key}")
        obj = s3.get_object(Bucket=bucket, Key=input_key)
        all_chunks = json.loads(obj['Body'].read().decode('utf-8'))
        
        # Extract text for encoding
        corpus_texts = [c.get('content') or c.get('text', '') for c in all_chunks]
        
        # 3. Generate Embeddings
        print(f"Generating embeddings for {len(corpus_texts)} chunks...")
        corpus_embs = model.encode(corpus_texts, convert_to_tensor=True )
        
        # 4. Convert Tensor to Numpy and Save as Compressed .npz
        # This is critical so the StoreQdrant Lambda doesn't need to install torch (800MB+)
        embeddings_np = corpus_embs.cpu().numpy()
        
        buffer = io.BytesIO()
        np.savez_compressed(buffer, embeddings=embeddings_np, chunks=all_chunks)
        buffer.seek(0)
        
        # 5. Upload compressed file to S3
        print(f"Uploading compressed NPZ to s3://{bucket}/{output_key}")
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
                "embedding_shape": list(embeddings_np.shape),
                "output_key": output_key
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}