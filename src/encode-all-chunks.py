import torch
from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1", device="cuda") # best perf model 

with open("../data/chunks/final_chunks.json") as f:
    all_chunks = json.load(f)

corpus_texts = [c['content'] for c in all_chunks]

corpus_embs = model.encode(corpus_texts, convert_to_tensor=True, show_progress_bar=True)

# we save the embeddings along with the chunks(content + metadata) for easy retrieval later
torch.save({"embeddings": corpus_embs, "chunks": all_chunks}, "../data/embedded/mxbai_corpus.pt")
