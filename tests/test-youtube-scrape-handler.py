import os
import json
from dotenv import load_dotenv
from lambdas.scrape_youtube.handler import lambda_handler  # adjust path if needed

load_dotenv()  # load AWS credentials and bucket name from .env

def test_youtube_lambda():
    class MockContext:
        def __init__(self):
            self.aws_request_id = "test-request-id-123"

    # ----------------------------
    # Build the event for Lambda
    # ----------------------------
    test_event = {
        "input_bucket": os.getenv("DATA_BUCKET_NAME"),   # e.g., "virtual-lenny-bucket"
        "video_ids_key": "data/raw/youtube/video_ids.txt",
        "output_bucket": os.getenv("DATA_BUCKET_NAME"),
        "output_prefix": "data/raw/youtube/transcripts/"
    }

    print("Starting Local Lambda Test...")

    # Call the Lambda handler
    response = lambda_handler(test_event, MockContext())

    # Parse the response
    status_code = response['statusCode']
    body = json.loads(response['body'])

    if status_code == 200:
        print("SUCCESS!")
        print(f"Videos Processed: {body['videos_processed']} / {body['total_videos']}")
    else:
        print("FAILED!")
        print(f"Error: {body.get('error')}")

if __name__ == "__main__":
    # check for AWS creds
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("Error: AWS credentials not found in environment.")
    elif not os.getenv("DATA_BUCKET_NAME"):
        print("Error: DATA_BUCKET_NAME not set in environment.")
    else:
        test_youtube_lambda()
