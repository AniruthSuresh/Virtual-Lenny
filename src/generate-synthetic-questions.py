import os
import json
import random
from google import genai
from tqdm import tqdm
from dotenv import load_dotenv
import requests

load_dotenv()

random.seed(42)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# -----------------------
# Load chunks
# -----------------------
with open("../data/chunks/final_chunks.json", "r") as f:
    all_chunks = json.load(f)

linkedin_chunks = [c for c in all_chunks if c["source"] == "linkedin"]
youtube_chunks = [c for c in all_chunks if c["source"] == "youtube"]

# -----------------------
# Dataset configs
# -----------------------
DATASETS = {
    "linkedin_only": {
        "chunks": random.sample(linkedin_chunks, min(50, len(linkedin_chunks))),
        "output": "../data/chunks/linkedin_50_questions.json",
    },
    "youtube_only": {
        "chunks": random.sample(youtube_chunks, min(50, len(youtube_chunks))),
        "output": "../data/chunks/youtube_50_questions.json",
    },
    "mixed_25_25": {
        "chunks": (
            random.sample(linkedin_chunks, min(25, len(linkedin_chunks)))
            + random.sample(youtube_chunks, min(25, len(youtube_chunks)))
        ),
        "output": "../data/chunks/mixed_25_25_questions.json",
    },
}



def generate_local(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:7b-instruct",
            "prompt": prompt,
            "temperature": 0.3,
            "stream": False
        }
    )
    return response.json()["response"].strip()


def generate_questions(chunks, output_path):
    gold_dataset = []

    print(f"\nGenerating {len(chunks)} questions → {output_path}")

    for chunk in tqdm(chunks):
        prompt = (
            "You are an expert at creating RAG evaluation datasets. "
            "Based on the context provided, write a short, natural-sounding question "
            "that this specific text answers perfectly. "
            "Do not mention 'the text' or 'the context'.\n\n"
            f"Context: {chunk['content']}"
        )

        try:
            """
            Gemini 2.5 flash --> ran out of quota
            So , using local model for now
            """
            # response = client.models.generate_content(
            #     model="gemini-2.5-flash",
            #     contents=prompt,
            # )

            # question = response.text.strip()

            question = generate_local(prompt)

            gold_dataset.append({
                "question": question,
                "correct_id": chunk["chunk_id"],
                "context": chunk["content"].strip(),
                "source": chunk["source"],
            })

        except Exception as e:
            print(f"\nError on chunk {chunk.get('chunk_id')}: {e}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(gold_dataset, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(gold_dataset)} questions")

# -----------------------
# Run all datasets
# -----------------------
for name, cfg in DATASETS.items():
    generate_questions(cfg["chunks"], cfg["output"])
