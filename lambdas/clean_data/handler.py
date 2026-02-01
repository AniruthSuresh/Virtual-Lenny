import json
import boto3
import re
import unicodedata
from typing import Dict

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Clean raw LinkedIn and YouTube data from S3.
    
    Expected event:
    {
        "input_bucket": "virtual-lenny-bucket",
        "input_prefixes": ["data/raw/linkedin/", "data/raw/youtube/transcripts/"],
        "output_bucket": "virtual-lenny-bucket",
        "output_prefixes": ["data/processed/linkedin/", "data/processed/youtube/"]
    }
    """

    print("Event Received:", event)
    try:
        cleaned_count = 0
        
        # Process each source type
        for input_prefix, output_prefix in zip(
            event['input_prefixes'],
            event['output_prefixes']
        ):
            source_type = 'linkedin' if 'linkedin' in input_prefix else 'youtube'
            
            # List all files in input prefix
            response = s3.list_objects_v2(
                Bucket=event['input_bucket'],
                Prefix=input_prefix
            )

            # print(response)
            
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                key = obj['Key']
                
                if not key.endswith('.json'):
                    continue
                
                # Read raw data
                raw_data = s3.get_object(
                    Bucket=event['input_bucket'],
                    Key=key
                )
                data = json.loads(raw_data['Body'].read())
                
                # Clean based on source type
                if source_type == 'linkedin':
                    cleaned_data = clean_linkedin_data(data)
                else:
                    cleaned_data = clean_youtube_data(data)

                output_key = key.replace(input_prefix, output_prefix)

                try:
                    s3.head_object(Bucket=event['output_bucket'], Key=output_key)
                    print(f"SKIPPING: {output_key} already exists")
                    continue
                except s3.exceptions.ClientError as e:

                    if e.response['Error']['Code'] == '404':
                        s3.put_object(
                            Bucket=event['output_bucket'],
                            Key=output_key,
                            Body=json.dumps(cleaned_data, indent=2, ensure_ascii=False),
                            ContentType='application/json'
                        )
                        cleaned_count += 1
                        print(f"Saved: {output_key}")
                    else:
                        raise
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'files_cleaned': cleaned_count
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def clean_linkedin_data(data: Dict) -> Dict:
    """Clean LinkedIn post data"""
    return {
        "source": "linkedin",
        "post_id": data.get("post_id"),
        "url": strip_tracking_params(data.get("url", "")),
        "author": data.get("author", "Lenny Rachitsky"),
        "posted_at": data.get("posted_at"),
        "likes": data.get("likes", 0),
        "text": clean_linkedin_text(data.get("text", ""))
    }


def clean_youtube_data(data: Dict) -> Dict:
    """Clean YouTube transcript data"""
    return {
        "source": "youtube",
        "video_id": data.get("video_id"),
        "url": data.get("url"),
        "text": clean_youtube_text(data.get("text", ""))
    }


def normalize_unicode(text: str) -> str:
    """
    Json renders " " as special unicode spaces -> so remove thosee
    Normalize smart quotes, apostrophes, dashes, ellipses, etc.
    """
    if not text:
        return ""
    
    text = unicodedata.normalize("NFKC", text)
    
    replacements = {
        """: '"',
        """: '"',
        "'": "'",
        "'": "'",
        "–": "-",
        "—": "-",
        "…": "...",
    }
    
    for src, tgt in replacements.items():
        text = text.replace(src, tgt)
    
    return text


def normalize_whitespace(text: str) -> str:
    """
    - Collapse all newlines to spaces
    - Collapse multiple spaces/tabs into a single space
    - Strip leading/trailing spaces
    """

    if not text:
        return ""
    
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def strip_tracking_params(url: str) -> str:
    """
    Remove LinkedIn tracking params like utm_source, rcm, etc.
    """
    if not url:
        return ""
    return url.split("?")[0]


def soften_ctas(text: str) -> str:
    """
    Remove aggressive CTA spam but keep intent.
    """
    patterns = [
        r"→\s*Subscribe.*",
        r"→\s*Listen now.*",
        r"Listen now\s*👇.*",
    ]
    
    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    
    return text.strip()


def clean_linkedin_text(text: str) -> str:
   
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    text = soften_ctas(text)
    return text


def clean_youtube_text(text: str) -> str:
    """
    Clean YouTube transcript text:
    - Normalize unicode characters
    - Remove '>>' speaker markers
    - Replace URLs with [LINK]
    - Collapse newlines and spaces
    """
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    
    # Remove speaker markers
    text = re.sub(r'>>\s*', '', text)
    
    # Replace URLs
    text = re.sub(r'https?://\S+', '[LINK]', text)
    
    # Collapse whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()