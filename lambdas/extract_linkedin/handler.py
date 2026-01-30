import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
client = ApifyClient(APIFY_TOKEN)


def lambda_handler(event, context):
    """
    Expected event:
    {
        "profile_url": "https://www.linkedin.com/in/lennyrachitsky/",
        "count": 100
    }
    """

    profile_url = event["profile_url"]
    count = event.get("count", 100)

    run_input = {
        "profileUrl": profile_url,
        "username": profile_url.split("/")[-2],
        "count": count,
        "limit": count
    }

    print(f"Triggering Apify for: {profile_url}")

    run = client.actor("apimaestro/linkedin-profile-posts").call(
        run_input=run_input
    )

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Found {len(items)} raw items")

    records = []

    for index, item in enumerate(items):
        # ---- Clean ID extraction ----
        raw_id_data = item.get("post_id")
        if isinstance(raw_id_data, dict):
            clean_id = (
                raw_id_data.get("activity_urn")
                or raw_id_data.get("ugcPost_urn")
                or f"post_{index}"
            )
        else:
            clean_id = raw_id_data or f"post_{index}"

        # ---- Date extraction ----
        posted_info = item.get("posted_at", {})
        if isinstance(posted_info, dict):
            date_str = posted_info.get("date") or posted_info.get("relative") or ""
        else:
            date_str = posted_info or ""

        # ---- Likes ----
        stats = item.get("stats", {})
        if isinstance(stats, dict):
            likes_count = stats.get("likes") or stats.get("total_reactions") or 0
        else:
            likes_count = item.get("likes") or item.get("numLikes") or 0

        # ---- Author ----
        author_info = item.get("author", {})
        if isinstance(author_info, dict):
            author_name = (
                author_info.get("name")
                or f"{author_info.get('firstName', '')} {author_info.get('lastName', '')}".strip()
            )
        else:
            author_name = ""

        if not author_name:
            author_name = "Lenny Rachitsky"

        record = {
            "source": "linkedin",
            "post_id": clean_id,
            "url": item.get("url", ""),
            "text": item.get("text", ""),
            "posted_at": date_str,
            "likes": likes_count,
            "author": author_name
        }

        records.append(record)

    return {
        "status": "ok",
        "source": "linkedin",
        "profile_url": profile_url,
        "count": len(records),
        "posts": records
    }
