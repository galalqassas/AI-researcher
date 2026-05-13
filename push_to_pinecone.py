import os
from pinecone import Pinecone, ServerlessSpec
from app.database import Session
from app.models.paper import Paper
from app.classification.qdrant_store import bytes_to_embed_local
from app.config import OLLAMA_EMBED_MODEL, QDRANT_EMBED_DIMENSION

API_KEY = "pcsk_5KdgZV_3kqARG9BYq2oTkn1tbCZfNyX4xW3Sjw2vUywLwzzWnyn7v8pBo8E9JzrqeFQ4Bq"
INDEX_NAME = "auto-researcher-papers"

def main():
    print("Initializing Pinecone client...")
    pc = Pinecone(api_key=API_KEY)
    
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index '{INDEX_NAME}' with dimension {QDRANT_EMBED_DIMENSION}...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=QDRANT_EMBED_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
    
    index = pc.Index(INDEX_NAME)
    
    print("Connecting to local SQLite database to fetch papers...")
    session = Session()
    try:
        papers = session.query(Paper).filter(Paper.embedding != None).all()
        print(f"Found {len(papers)} papers with embeddings.")
        
        if not papers:
            print("No vectors to push.")
            return

        batch = []
        for p in papers:
            vec = bytes_to_embed_local(p.embedding)
            batch.append({
                "id": str(p.id),  # Pinecone requires string IDs
                "values": vec.tolist(),
                "metadata": {
                    "arxiv_id": p.arxiv_id,
                    "title": p.title,
                    "model": OLLAMA_EMBED_MODEL
                }
            })
        
        print("Pushing vectors to Pinecone in batches...")
        # Upsert in chunks of 100 to avoid request size limits
        chunk_size = 100
        for i in range(0, len(batch), chunk_size):
            chunk = batch[i:i + chunk_size]
            index.upsert(vectors=chunk)
            print(f"Upserted {len(chunk)} vectors (batch {i//chunk_size + 1}).")
            
        print("Success! All vectors pushed to Pinecone.")
        
        # Verify stats
        stats = index.describe_index_stats()
        print("Pinecone index stats:", stats)
            
    finally:
        session.close()

if __name__ == "__main__":
    main()
