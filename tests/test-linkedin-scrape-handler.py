import os
import json
import sys
from dotenv import load_dotenv
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from lambdas.scrape_linkedin.handler import lambda_handler

load_dotenv() 

def test_linkedin_lambda():

    class MockContext:
        def __init__(self):
            self.aws_request_id = "test-request-id-123"

    # 2. Define your test event
    # Ensure this bucket actually exists in your AWS account
    test_event = {
        "profile_url": "https://www.linkedin.com/in/lennyrachitsky/",
        "count": 5,  # Keep it small for testing to save Apify credits
        "output_bucket": os.getenv("DATA_BUCKET_NAME"), 
        "output_prefix": "test/raw/linkedin/"
    }

    print(" Starting Local Lambda Test...")
    
    response = lambda_handler(test_event, MockContext())

    status_code = response['statusCode']
    body = json.loads(response['body'])

    if status_code == 200:
        print(" SUCCESS!")
        print(f" Posts Scraped: {body['posts_scraped']}")
        print(f" Location: {body['output_location']}")
    else:
        print(" FAILED!")
        print(f"Error: {body.get('error')}")

if __name__ == "__main__":
    if not os.getenv("APIFY_TOKEN"):
        print(" Error: APIFY_TOKEN not found in environment.")
    else:
        test_linkedin_lambda()

