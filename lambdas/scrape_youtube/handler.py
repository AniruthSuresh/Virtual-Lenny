import json
import boto3
import os
from youtube_transcript_api import YouTubeTranscriptApi
import re

s3 = boto3.client('s3')

def s3_object_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def lambda_handler(event, context):
    """
    Scrape YouTube transcripts for a list of video IDs.
    
    Expected event:
    {
        "input_bucket": "virtual-lenny-bucket",
        "video_ids_key": "data/raw/youtube/video_ids.txt",
        "output_bucket": "virtual-lenny-bucket",
        "output_prefix": "data/raw/youtube/transcripts/"
    }
    """
    try:
        # Get video IDs from S3
        video_ids = get_video_ids_from_s3(
            event['input_bucket'],
            event['video_ids_key']
        )
        
        print(f"Processing {len(video_ids)} videos")
        
        # Process each video
        success_count = 0
        for video_id in video_ids:
            key = f"{event['output_prefix']}{video_id}.json"

            if s3_object_exists(event['output_bucket'], key):
                print(f"Skipping {video_id}, already exists in S3")
                continue

            try:
                transcript = fetch_and_clean_transcript(video_id)

                if not transcript:
                    print(f"No transcript for {video_id}")
                    continue

                record = {
                    "source": "youtube",
                    "video_id": video_id,
                    "url": f"https://youtu.be/{video_id}",
                    "text": transcript
                }

                s3.put_object(
                    Bucket=event['output_bucket'],
                    Key=key,
                    Body=json.dumps(record, indent=2),
                    ContentType='application/json'
                )

                success_count += 1
                print(f"Saved {video_id} ({len(transcript)} chars)")

            except Exception as e:
                print(f"Error processing {video_id}: {str(e)}")
                continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'videos_processed': success_count,
                'total_videos': len(video_ids)
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def get_video_ids_from_s3(bucket: str, key: str) -> list:
    """Read video IDs from S3 text file"""
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    
    # Parse tab-separated file
    video_ids = []
    for line in content.strip().split('\n'):
        if '\t' in line:
            video_id = line.split('\t')[0]
            video_ids.append(video_id)
    
    return video_ids


def fetch_and_clean_transcript(video_id: str) -> str:
    """
    Fetch and clean YouTube transcript.
    
    This is your existing logic from scrape-youtube.py
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(["en"])
        transcript_data = transcript.fetch()
        
        # Combine chunks
        raw_text = " ".join(chunk['text'] for chunk in transcript_data)
        
        # Clean text
        text = clean_transcript(raw_text)
        
        return text
        
    except Exception as e:
        print(f"Transcript fetch failed for {video_id}: {str(e)}")
        return None


def clean_transcript(text: str) -> str:
    """Clean YouTube transcript text"""
    if not text:
        return ""
    
    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ")
    
    # Remove excessive newlines
    text = re.sub(r"\n+", " ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()