"""Pinecone vector database client — collection management, upsert, and search."""

import logging
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from app.config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_EMBED_DIMENSION,
    OLLAMA_EMBED_MODEL,
)

log = logging.getLogger(__name__)

_pc_client = None

try:
    if PINECONE_API_KEY:
        _pc_client = Pinecone(api_key=PINECONE_API_KEY)
        log.info(f"Pinecone client initialized")
    else:
        log.warning("Pinecone API key not found in environment.")
except Exception as e:
    log.warning(f"Pinecone client init failed: {e}")
    _pc_client = None


def get_client():
    """Return the singleton Pinecone client, or None if unavailable."""
    return _pc_client


def get_index(collection_name: str = PINECONE_INDEX_NAME):
    client = get_client()
    if client is None:
        return None
    return client.Index(collection_name)


def ensure_collection(collection_name: str = PINECONE_INDEX_NAME):
    """Create the Pinecone index if it doesn't already exist."""
    client = get_client()
    if client is None:
        return
    existing = [idx.name for idx in client.list_indexes()]
    if collection_name not in existing:
        client.create_index(
            name=collection_name,
            dimension=PINECONE_EMBED_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        log.info(f"Created Pinecone index '{collection_name}' (dim={PINECONE_EMBED_DIMENSION}, cosine)")


def upsert_papers_batch(
    papers: list[dict],
    collection_name: str = PINECONE_INDEX_NAME,
):
    """Upsert multiple papers at once.

    Each dict must have: id, arxiv_id, title, embedding (np.ndarray).
    """
    if not papers:
        return
    client = get_client()
    if client is None:
        log.error("Pinecone client not available — skipping batch upsert")
        return
    ensure_collection(collection_name)
    index = get_index(collection_name)
    if index is None:
        return
        
    points = []
    for p in papers:
        points.append({
            "id": str(p["id"]),
            "values": p["embedding"].tolist(),
            "metadata": {
                "arxiv_id": p["arxiv_id"],
                "title": p["title"],
                "model": OLLAMA_EMBED_MODEL,
            }
        })
    index.upsert(vectors=points)
    log.info(f"Upserted {len(points)} paper vectors into Pinecone '{collection_name}'")


def search_similar(
    query_vector: np.ndarray,
    limit: int = 10,
    collection_name: str = PINECONE_INDEX_NAME,
) -> list[dict]:
    """Search for the most similar papers to a query vector.

    Returns list of dicts with 'id', 'score', 'payload', or empty list if Pinecone unavailable.
    """
    index = get_index(collection_name)
    if index is None:
        return []
    
    hits = index.query(
        vector=query_vector.tolist(),
        top_k=limit,
        include_metadata=True,
    )
    results = []
    for hit in hits.get("matches", []):
        results.append({
            "id": int(hit.id),
            "score": hit.score,
            "payload": hit.metadata,
        })
    return results


def delete_points(
    point_ids: list[int],
    collection_name: str = PINECONE_INDEX_NAME,
):
    """Delete vectors from Pinecone by their point IDs."""
    index = get_index(collection_name)
    if index is None:
        return
    # Convert IDs to strings for Pinecone
    str_ids = [str(pid) for pid in point_ids]
    index.delete(ids=str_ids)
    log.debug(f"Deleted {len(point_ids)} points from Pinecone '{collection_name}'")


def get_collection_info(collection_name: str = PINECONE_INDEX_NAME):
    """Return collection info dict or None if collection doesn't exist / Pinecone unavailable."""
    index = get_index(collection_name)
    if index is None:
        return None
    try:
        stats = index.describe_index_stats()
        return {
            "points_count": stats.total_vector_count,
            "indexed_vectors_count": stats.total_vector_count,
            "status": "ready",
        }
    except Exception as e:
        log.error(f"Failed to get Pinecone index info: {e}")
        return None


def resync_embeddings():
    """Synchronize SQLite embeddings into Pinecone."""
    from app.database import Session
    from app.models.paper import Paper

    client = get_client()
    if client is None:
        log.error("Pinecone client not available — cannot resync")
        return 0

    ensure_collection()
    collection_info = get_collection_info()
    if collection_info is None:
        log.error("Could not get Pinecone index info — cannot resync")
        return 0

    session = Session()
    try:
        papers_with_embeddings = session.query(Paper).filter(Paper.embedding != None).all()
        if not papers_with_embeddings:
            log.info("No papers with embeddings found in SQLite")
            return 0

        # Since Pinecone doesn't have an easy scroll API to get all IDs like Pinecone,
        # we will fetch existing IDs by checking them in batches.
        index = get_index()
        all_ids = [str(p.id) for p in papers_with_embeddings]
        
        batch = []
        # Check existence in chunks of 1000
        chunk_size = 1000
        for i in range(0, len(all_ids), chunk_size):
            chunk_ids = all_ids[i:i+chunk_size]
            fetch_res = index.fetch(ids=chunk_ids)
            existing_ids = set(fetch_res.get("vectors", {}).keys())
            
            for p in papers_with_embeddings[i:i+chunk_size]:
                if str(p.id) not in existing_ids and p.embedding is not None:
                    vec = bytes_to_embed_local(p.embedding)
                    batch.append({
                        "id": p.id,
                        "arxiv_id": p.arxiv_id,
                        "title": p.title,
                        "embedding": vec,
                    })

        if batch:
            # Upsert in chunks of 100
            for i in range(0, len(batch), 100):
                upsert_papers_batch(batch[i:i+100])
            log.info(f"Re-synced {len(batch)} papers from SQLite to Pinecone")
        else:
            log.info("Pinecone is in sync — no papers to resync")

        return len(batch)
    except Exception as e:
        log.error(f"Resync failed: {e}")
        return 0
    finally:
        session.close()


def bytes_to_embed_local(data: bytes) -> np.ndarray:
    """Deserialize bytes back to numpy embedding (local copy to avoid circular import)."""
    import struct
    n = len(data) // 4
    return np.array(struct.unpack(f"{n}f", data), dtype=np.float32)
