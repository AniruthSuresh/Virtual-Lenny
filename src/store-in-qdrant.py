from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import torch
import uuid


DATA_PATH = "../data/embedded/mxbai_corpus.pt"
COLLECTION = "virtual-lenny"
BATCH_SIZE = 500  # adjust if needed

client = QdrantClient(host="localhost", port=6333)

# Load embeddings + chunks
data = torch.load(DATA_PATH)
embeddings = data["embeddings"]
chunks = data["chunks"]

# Create collection (overwrite if exists)
if COLLECTION in [c.name for c in client.get_collections().collections]:
    client.delete_collection(collection_name=COLLECTION)

client.create_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE)
)

# Upsert in batches
for start_idx in range(0, len(chunks), BATCH_SIZE):
    batch_chunks = chunks[start_idx:start_idx+BATCH_SIZE]
    batch_embs = embeddings[start_idx:start_idx+BATCH_SIZE]

    points = []
    for i, chunk in enumerate(batch_chunks):
        points.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_OID, chunk["chunk_id"])),  # deterministic UUID
            "vector": embeddings[i].tolist(),
            "payload": chunk
        })

    client.upsert(
        collection_name=COLLECTION,
        points=points
    )

    print(f"Upserted {start_idx} to {start_idx+len(batch_chunks)} points")

print(f"Finished uploading {len(chunks)} vectors to Qdrant!")
