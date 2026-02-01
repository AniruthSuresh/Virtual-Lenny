import os
import json
from dotenv import load_dotenv

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from lambdas.generate_embeddings.handler import lambda_handler

load_dotenv()

class MockContext:
    def __init__(self):
        self.aws_request_id = "test-embed-id-999"

def test_embedding_lambda():
    test_event = {
        "bucket": os.getenv("DATA_BUCKET_NAME"),
        "input_key": "data/chunks/final_chunks.json",
        "output_key": "data/embedded/mxbai_corpus.pt"
    }

    print("Starting Embedding Test (this may take a minute)...")
    response = lambda_handler(test_event, MockContext())
    
    if response["statusCode"] == 200:
        body = json.loads(response["body"])
        print("SUCCESS!")
        print(f"Vector Shape: {body['embedding_shape']}")
        print(f"Saved to: {body['output_key']}")
    else:
        print(f"FAILED: {response['body']}")

if __name__ == "__main__":
    test_embedding_lambda()

