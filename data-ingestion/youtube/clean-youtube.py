import os
import json
import re
import unicodedata
from tqdm import tqdm


RAW_DIR = "../../data/raw/youtube/transcripts"        # original JSON files
CLEAN_DIR = "../../data/processed/youtube"    # cleaned JSON output

os.makedirs(CLEAN_DIR, exist_ok=True)

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

    # 1. Normalize unicode
    text = unicodedata.normalize("NFKC", text)

    # 2. Remove YouTube speaker markers
    text = re.sub(r'>>\s*', '', text)

    # 3. Replace URLs with placeholder
    text = re.sub(r'https?://\S+', '[LINK]', text)

    # 4. Collapse multiple newlines / whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # 5. Strip leading/trailing spaces
    return text.strip()


def main():
    files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]
    print(f"[INFO] Found {len(files)} YouTube videos to process")

    for filename in tqdm(files, desc="Cleaning YouTube transcripts"):
        in_path = os.path.join(RAW_DIR, filename)
        out_path = os.path.join(CLEAN_DIR, filename)

        if os.path.exists(out_path):
            continue

        with open(in_path, "r") as f:
            data = json.load(f)

        cleaned_text = clean_youtube_text(data.get("text", ""))

        cleaned_data = {
            "source": "youtube",
            "video_id": data.get("video_id"),
            "url": data.get("url"),
            "text": cleaned_text,
        }

        with open(out_path, "w") as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Cleaned YouTube data saved to {CLEAN_DIR}")


if __name__ == "__main__":
    main()
