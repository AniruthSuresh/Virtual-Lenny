import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

client = ApifyClient(APIFY_TOKEN)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw/linkedin")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def scrape_linkedin_posts(profile_url, count=100):

    run_input = {
        "profileUrl": profile_url,
        "username": profile_url.split("/")[-2], 
        "count": count,
        "limit": count
    }

    print(f" Triggering Apify for: {profile_url}")
    try:
        run = client.actor("apimaestro/linkedin-profile-posts").call(run_input=run_input)
        
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"📦 Found {len(items)} raw items in dataset.")

        for index, item in enumerate(items):
            # 1. Clean ID extraction
            raw_id_data = item.get("post_id")
            if isinstance(raw_id_data, dict):
                clean_id = raw_id_data.get("activity_urn") or raw_id_data.get("ugcPost_urn") or f"post_{index}"
            else:
                clean_id = raw_id_data or f"post_{index}"
            
            # 2. FLATTENING NESTED DATA
            posted_info = item.get("posted_at", {})
            date_str = ""
            if isinstance(posted_info, dict):
                date_str = posted_info.get("date") or posted_info.get("relative") or ""
            else:
                date_str = posted_info or ""

            stats = item.get("stats", {})
            likes_count = 0
            if isinstance(stats, dict):
                likes_count = stats.get("likes") or stats.get("total_reactions") or 0
            else:
                likes_count = item.get("likes") or item.get("numLikes") or 0

            author_info = item.get("author", {})
            author_name = ""
            if isinstance(author_info, dict):
                author_name = author_info.get("name") or f"{author_info.get('firstName', '')} {author_info.get('lastName', '')}".strip()
            
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

            safe_id = "".join([c for c in str(clean_id) if c.isalnum() or c in ("_", "-")])
            file_path = os.path.join(OUTPUT_DIR, f"{safe_id}.json")
            
            with open(file_path, "w") as f:
                json.dump(record, f, indent=2)

        print(f"Successfully saved {len(items)} files to {OUTPUT_DIR}")

    except Exception as e:
        print(f"Error during scraping: {e}")

if __name__ == "__main__":
    
    LENNY_PROFILE = "https://www.linkedin.com/in/lennyrachitsky/"
    scrape_linkedin_posts(LENNY_PROFILE)