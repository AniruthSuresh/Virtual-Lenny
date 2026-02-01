"""
This script retrieves video IDs from a specified YouTube playlist and checks
for the availability of English transcripts. It saves up to 100 video IDs that
have transcripts to a text file.

NOTE : This id's generated needs to pushed to s3 bucket to be used by the scrape_youtube lambda function
use the helpers/push-youtube-id-s3.py script for that

"""

import subprocess
import os
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL2fLjt2dG0N6unOOF3nHWYGcJJIQR1NKm"
MAX_VIDEOS = 100

OUTPUT_DIR = "../data/raw/youtube"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "video_ids.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_video_ids(playlist_url):
    """
    Uses yt-dlp to reliably extract video IDs from a playlist.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--get-id",
        playlist_url,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip().split("\n")


def has_transcript(video_id):
    """
    Checks whether an English transcript exists for a video.
    Issue : Some vidoes may not have transcripts or have them disabled / in my case : it was private 
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript_list.find_transcript(["en"])
        return True
    except (NoTranscriptFound, TranscriptsDisabled):
        return False
    except Exception as e:
        print(f"[ERROR] Transcript check failed for {video_id}: {e}")
        return False


if __name__ == "__main__":
    all_ids = get_video_ids(PLAYLIST_URL)

    valid_ids = []
    print(f"[INFO] Found {len(all_ids)} total videos, checking transcripts...")

    for vid in all_ids:
        if len(valid_ids) >= MAX_VIDEOS:
            break

        if has_transcript(vid):
            valid_ids.append(vid)
            print(f"[OK] Transcript found: {vid}")
        else:
            print(f"[SKIP] No transcript: {vid}")

    with open(OUTPUT_FILE, "w") as f:
        for vid in valid_ids:
            f.write(f"{vid}\thttps://youtu.be/{vid}\n")

    print(f"\n[DONE] Saved {len(valid_ids)} transcript-ready video IDs to {OUTPUT_FILE}")
