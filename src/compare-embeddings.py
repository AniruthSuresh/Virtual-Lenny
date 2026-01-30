import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv
import torch
import time


load_dotenv()

with open("../data/chunks/final_chunks.json", "r") as f:
    all_chunks = json.load(f)

with open("../data/chunks/youtube_50_questions.json", "r") as f:
    gold_set = json.load(f)

corpus_texts = [c['content'] for c in all_chunks]
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_openai_embeddings(texts):
    response = client.embeddings.create(input=texts, model="text-embedding-3-large")
    return np.array([res.embedding for res in response.data])

def evaluate_model(name, model_type="local", path=None):
    print(f"\n Evaluating {name}...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    if model_type == "local":
        model = SentenceTransformer(path, device=device)

        corpus_embs = model.encode(
            corpus_texts,
            convert_to_tensor=True,
            show_progress_bar=True
        )

    else:
        # OpenAI runs on remote GPUs (cannot change)
        corpus_embs = get_openai_embeddings(corpus_texts)
        corpus_embs = util.normalize_embeddings(corpus_embs)

    metrics = {
        "MRR": 0.0,
        "HitRate@5": 0.0,
        "AvgQueryTimeSec": 0.0,
    }

    total_query_time = 0.0

    for item in tqdm(gold_set, desc=f"{name} Queries"):
        query = item["question"]
        correct_id = item["correct_id"]

        start = time.perf_counter()

        if model_type == "local":
            query_emb = model.encode(query, convert_to_tensor=True)

            search_results = util.semantic_search(
                query_emb, corpus_embs, top_k=10
            )[0]

        else:
            query_emb = get_openai_embeddings([query])[0]
            scores = np.dot(corpus_embs, query_emb)
            top_indices = np.argsort(scores)[::-1][:10]
            search_results = [{"corpus_id": idx} for idx in top_indices]

        total_query_time += (time.perf_counter() - start)

        retrieved_ids = [
            all_chunks[res["corpus_id"]]["chunk_id"]
            for res in search_results
        ]

        if correct_id in retrieved_ids[:5]:
            metrics["HitRate@5"] += 1
            rank = retrieved_ids.index(correct_id) + 1
            metrics["MRR"] += 1.0 / rank

    num_queries = len(gold_set)

    metrics["MRR"] = round(metrics["MRR"] / num_queries, 4)
    metrics["HitRate@5"] = round(metrics["HitRate@5"] / num_queries, 4)
    metrics["AvgQueryTimeSec"] = round(total_query_time / num_queries, 4)

    print(f"\n Results for {name}:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    return metrics



results = {
    "mxbai-v1": evaluate_model("mxbai-v1", "local", "mixedbread-ai/mxbai-embed-large-v1"),
    "UAE-Large-V1": evaluate_model("UAE-Large-V1", "local", "WhereIsAI/UAE-Large-V1"),
    "all-MiniLM-L6-v2": evaluate_model("all-MiniLM-L6-v2", "local", "sentence-transformers/all-MiniLM-L6-v2"),
    "all-mpnet-base-v2": evaluate_model("all-mpnet-base-v2", "local", "sentence-transformers/all-mpnet-base-v2"),
    "sentence-T5-base": evaluate_model("sentence-T5-base", "local", "sentence-transformers/sentence-T5-base"),
    # "OpenAI-3-Large": evaluate_model("OpenAI-3-Large", "api")
}


print("\n" + "="*40 + "\n FINAL LEADERBOARD\n" + "="*40)

OUTPUT_PATH = "../results/youtube-testing-embeddings.json"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w") as f:
    json.dump(results, f, indent=4)

print(f"\nResults saved to {OUTPUT_PATH}")


