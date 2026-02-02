from sentence_transformers import SentenceTransformer
import json
import numpy as np
import boto3
import os

# -------- config --------
LOCAL_PATH = "../data/embedded/mxbai_corpus.npz"
S3_BUCKET = "virtual-lenny-bucket"
S3_KEY = "data/embedded/mxbai_corpus.npz"  # exact same path
# ------------------------

model = SentenceTransformer(
    "mixedbread-ai/mxbai-embed-large-v1",
    device="cuda"
)

with open("../data/chunks/final_chunks.json") as f:
    all_chunks = json.load(f)

corpus_texts = [c["content"] for c in all_chunks]

corpus_embs = model.encode(
    corpus_texts,
    convert_to_tensor=True,
    show_progress_bar=True
)

# move to cpu + numpy
embeddings_np = corpus_embs.detach().cpu().numpy()

# save as npz
np.savez(
    LOCAL_PATH,
    embeddings=embeddings_np,
    chunks=np.array(all_chunks, dtype=object)
)

print(f"Saved embeddings locally to {LOCAL_PATH}")

# -------- upload to S3 --------
s3 = boto3.client("s3")

s3.upload_file(
    Filename=LOCAL_PATH,
    Bucket=S3_BUCKET,
    Key=S3_KEY
)

print(f"Uploaded to s3://{S3_BUCKET}/{S3_KEY}")
