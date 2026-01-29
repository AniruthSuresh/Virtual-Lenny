import os
import json
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
from tqdm import tqdm
import re


"""
IMPORTANT:

- Currently , most of the available source code are outdated due to YouTubeTranscriptApi changes. This script
Uses the updated transcript API flow: https://github.com/langchain-ai/langchain-community/issues/290#issuecomment-3301428239 (still a PR )
"""

INPUT_FILE = "../data/raw/youtube/video_ids.txt"
OUTPUT_DIR = "../data/raw/youtube/transcripts"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)
    transcript = transcript_list.find_transcript(["en"])
    transcript_data = transcript.fetch()

    # print(transcript_data)
    return " ".join(chunk.text for chunk in transcript_data)


def clean_transcript(text: str) -> str:
    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ")

    # Remove excessive newlines
    text = re.sub(r"\n+", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def main():
    with open(INPUT_FILE, "r") as f:
        lines = f.readlines()

    print(f"[INFO] Found {len(lines)} videos to process")

    for line in tqdm(lines, desc="Scraping YouTube transcripts"):
        video_id, url = line.strip().split("\t")

        # print(video_id)
        out_path = os.path.join(OUTPUT_DIR, f"{video_id}.json")

        if os.path.exists(out_path):
            print(f"[SKIP] Already exists: {video_id}")
            continue

        raw_text = fetch_transcript(video_id)
        if not raw_text:
            print(f"[SKIP] No transcript for {video_id}")
            continue

        text = clean_transcript(raw_text)

        if not text:
            print(f"[SKIP] No transcript for {video_id}")
            continue

        record = {
            "source": "youtube",
            "video_id": video_id,
            "url": url,
            "text": text,
        }

        with open(out_path, "w") as f:
            json.dump(record, f, indent=2)

        print(f"[OK] Saved {video_id} ({len(text)} chars)")


if __name__ == "__main__":
    main()
