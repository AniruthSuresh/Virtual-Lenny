import json
import boto3
import numpy as np
import uuid
import tempfile
import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Store embeddings in Qdrant Cloud vector database.
    
    Expected event:
    {
        "input_bucket": "virtual-lenny-bucket",
        "embeddings_key": "data/embeddings/mxbai_corpus.pt",
        "collection_name": "virtual-lenny",
        "qdrant_url": "https://your-cluster.aws.cloud.qdrant.io",
        "qdrant_api_key": "your-api-key", 
        "recreate_collection": false,
        "batch_size": 100
    }
    """
    try:
        input_bucket = event['input_bucket']
        embeddings_key = event['embeddings_key']
        collection_name = event.get('collection_name', 'virtual-lenny')
        qdrant_url = event.get('qdrant_url') or os.environ.get('QDRANT_URL')
        qdrant_api_key = event.get('qdrant_api_key') or os.environ.get('QDRANT_API_KEY')
        recreate = event.get('recreate_collection', False)
        batch_size = event.get('batch_size', 100)
        
        if not qdrant_url:
            raise ValueError("qdrant_url must be provided in event or QDRANT_URL env var")
        if not qdrant_api_key:
            raise ValueError("qdrant_api_key must be provided in event or QDRANT_API_KEY env var")
        
        print(f" Connecting to Qdrant Cloud at {qdrant_url}")
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            port=None # because : https://github.com/qdrant/qdrant-client/issues/394#issuecomment-2075283788
        )
        
        try:
            collections_list = client.get_collections()
            print(f" Connected! Found {len(collections_list.collections)} existing collections")
        except Exception as e:
            raise Exception(f"Failed to connect to Qdrant Cloud: {str(e)}")

        existing_collections = [c.name for c in collections_list.collections]
        
        if collection_name in existing_collections:
            collection_info = client.get_collection(collection_name=collection_name)
            points_count = collection_info.points_count
            
            print(f" Collection '{collection_name}' exists with {points_count} points")
            
            if points_count > 0 and not recreate:
                print(f" SKIPPING: Collection already populated with {points_count} vectors")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Collection already exists and is populated',
                        'collection_name': collection_name,
                        'existing_points': points_count,
                        'skipped': True
                    })
                }
            
            if recreate:
                print(f" Deleting existing collection for fresh upload...")
                client.delete_collection(collection_name=collection_name)
        
        # print(f"⬇Downloading embeddings from s3://{input_bucket}/{embeddings_key}")
        # with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
        #     s3.download_file(input_bucket, embeddings_key, tmp.name)
            
        #     print(" Loading embeddings file...")
        #     data = torch.load(tmp.name, map_location='cpu')
        #     embeddings = data["embeddings"]
        #     chunks = data["chunks"]
            
        #     os.unlink(tmp.name)
        
        print(f"⬇Downloading embeddings from s3://{input_bucket}/{embeddings_key}")
        with tempfile.NamedTemporaryFile(suffix='.npz', delete=False) as tmp:
            s3.download_file(input_bucket, embeddings_key, tmp.name)
            
            print(" Loading embeddings file...")
            # Use np.load instead of torch.load
            with np.load(tmp.name, allow_pickle=True) as data:
                embeddings = data["embeddings"]
                # If chunks was saved as a single object array, use .item()
                chunks = data["chunks"]
                if chunks.dtype == object and chunks.ndim == 0:
                    chunks = chunks.item()
            
            os.unlink(tmp.name)

        print(f"Loaded {len(chunks)} chunks with embeddings of dimension {embeddings.shape[1]}")
        
        # Create collection if it doesn't exist
        if collection_name not in existing_collections or recreate:
            print(f"Creating collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embeddings.shape[1],
                    distance=Distance.COSINE
                )
            )
        
        print(f"⬆ Uploading vectors in batches of {batch_size}...")
        total_uploaded = 0
        
        for start_idx in range(0, len(chunks), batch_size):
            end_idx = min(start_idx + batch_size, len(chunks))
            batch_chunks = chunks[start_idx:end_idx]
            batch_embs = embeddings[start_idx:end_idx]
            
            points = []
            # for i, chunk in enumerate(batch_chunks):
            #     # Create deterministic UUID from chunk_id
            #     point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, chunk["chunk_id"]))
                
            #     points.append(
            #         PointStruct(
            #             id=point_id,
            #             vector=batch_embs[i].tolist(),
            #             payload=chunk
            #         )
            #     )

            for i, chunk in enumerate(batch_chunks):
                # Create deterministic UUID from chunk_id
                point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, chunk["chunk_id"]))

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=batch_embs[i].tolist(), # Direct numpy to list conversion
                        payload=chunk
                    )
                )

            # Upsert batch to Qdrant Cloud
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            total_uploaded += len(points)
            print(f"✓ Uploaded {total_uploaded}/{len(chunks)} vectors ({(total_uploaded/len(chunks)*100):.1f}%)")
        
        
        collection_info = client.get_collection(collection_name=collection_name)
        
        print(f" Successfully uploaded {total_uploaded} vectors to Qdrant Cloud")
        print(f" Collection now has {collection_info.points_count} total points")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'collection_name': collection_name,
                'vectors_uploaded': total_uploaded,
                'collection_points_count': collection_info.points_count,
                'qdrant_url': qdrant_url,
                'skipped': False
            })
        }
        
    except Exception as e:
        print(f" Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
