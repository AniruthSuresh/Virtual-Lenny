import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

with open("../data/chunks/final_chunks.json", "r") as f:
    all_chunks = json.load(f)
with open("../data/chunks/linkedin-synthetic-questions.json", "r") as f:
    gold_set = json.load(f)

corpus_texts = [c['content'] for c in all_chunks]
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_openai_embeddings(texts):
    response = client.embeddings.create(input=texts, model="text-embedding-3-large")
    return np.array([res.embedding for res in response.data])

def evaluate_model(name, model_type="local", path=None):
    print(f"\n Evaluating {name}...")
    
    if model_type == "local":
        model = SentenceTransformer(path)
        corpus_embs = model.encode(corpus_texts, convert_to_tensor=True, show_progress_bar=True)
    else:
        # OpenAI handles large batches, but we'll do one shot for corpus
        corpus_embs = get_openai_embeddings(corpus_texts)
        corpus_embs = util.normalize_embeddings(corpus_embs) # Ensure cosine similarity works


    metrics = {"MRR": 0, "HitRate@5": 0}
    
    for item in tqdm(gold_set, desc=f"{name} Queries"):
        query = item['question']
        correct_id = item['correct_id']
        
        if model_type == "local":
            query_emb = model.encode(query, convert_to_tensor=True)
            search_results = util.semantic_search(query_emb, corpus_embs, top_k=10)[0]
        else:
            query_emb = get_openai_embeddings([query])[0]
            # Use dot product for normalized embeddings (same as cosine)
            scores = np.dot(corpus_embs, query_emb)
            top_indices = np.argsort(scores)[::-1][:10]
            search_results = [{"corpus_id": idx} for idx in top_indices]

        retrieved_ids = [all_chunks[res['corpus_id']]['chunk_id'] for res in search_results]
        
        if correct_id in retrieved_ids[:5]:
            metrics["HitRate@5"] += 1
            rank = retrieved_ids.index(correct_id) + 1
            metrics["MRR"] += 1.0 / rank

    num_queries = len(gold_set)
    return {k: round(v / num_queries, 4) for k, v in metrics.items()}


results = {
    "mxbai-v1": evaluate_model("mxbai-v1", "local", "mixedbread-ai/mxbai-embed-large-v1"),
    "UAE-Large-V1": evaluate_model("UAE-Large-V1", "local", "WhereIsAI/UAE-Large-V1"),
    "OpenAI-3-Large": evaluate_model("OpenAI-3-Large", "api")
}

print("\n" + "="*40 + "\n FINAL LEADERBOARD\n" + "="*40)

OUTPUT_PATH = "../results/only-linkedin-testing.json"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w") as f:
    json.dump(results, f, indent=4)

print(f"\nResults saved to {OUTPUT_PATH}")

