"""Qdrant vector database client — collection management, upsert, and search."""

import logging
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)
from app.config import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    QDRANT_EMBED_DIMENSION,
    OLLAMA_EMBED_MODEL,
)

log = logging.getLogger(__name__)

_qdrant_client: QdrantClient | None = None

try:
    _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    log.info(f"Qdrant client initialized ({QDRANT_HOST}:{QDRANT_PORT})")
except Exception as e:
    log.warning(f"Qdrant client init failed: {e}")
    _qdrant_client = None


def get_client() -> QdrantClient | None:
    """Return the singleton Qdrant client, or None if unavailable."""
    return _qdrant_client


def ensure_collection(collection_name: str = QDRANT_COLLECTION):
    """Create the collection if it doesn't already exist."""
    client = get_client()
    if client is None:
        return
    existing = client.get_collections().collections
    names = [c.name for c in existing]
    if collection_name not in names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=QDRANT_EMBED_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
        log.info(f"Created Qdrant collection '{collection_name}' (dim={QDRANT_EMBED_DIMENSION}, cosine)")


def upsert_papers_batch(
    papers: list[dict],
    collection_name: str = QDRANT_COLLECTION,
):
    """Upsert multiple papers at once.

    Each dict must have: id, arxiv_id, title, embedding (np.ndarray).
    """
    if not papers:
        return
    client = get_client()
    if client is None:
        log.error("Qdrant client not available — skipping batch upsert")
        return
    ensure_collection(collection_name)
    points = []
    for p in papers:
        points.append(
            PointStruct(
                id=p["id"],
                vector=p["embedding"].tolist(),
                payload={
                    "arxiv_id": p["arxiv_id"],
                    "title": p["title"],
                    "model": OLLAMA_EMBED_MODEL,
                },
            )
        )
    client.upsert(collection_name=collection_name, points=points)
    log.info(f"Upserted {len(points)} paper vectors into Qdrant '{collection_name}'")


def search_similar(
    query_vector: np.ndarray,
    limit: int = 10,
    collection_name: str = QDRANT_COLLECTION,
) -> list[dict]:
    """Search for the most similar papers to a query vector.

    Returns list of dicts with 'id', 'score', 'payload', or empty list if Qdrant unavailable.
    """
    client = get_client()
    if client is None:
        return []
    hits = client.query_points(
        collection_name=collection_name,
        query=query_vector.tolist(),
        limit=limit,
        with_payload=True,
    )
    results = []
    for hit in hits.points:
        results.append({
            "id": hit.id,
            "score": hit.score,
            "payload": hit.payload,
        })
    return results


def delete_points(
    point_ids: list[int],
    collection_name: str = QDRANT_COLLECTION,
):
    """Delete vectors from Qdrant by their point IDs."""
    client = get_client()
    if client is None:
        return
    client.delete(
        collection_name=collection_name,
        points_selector=point_ids,
    )
    log.debug(f"Deleted {len(point_ids)} points from Qdrant '{collection_name}'")


def get_collection_info(collection_name: str = QDRANT_COLLECTION):
    """Return collection info dict or None if collection doesn't exist / Qdrant unavailable."""
    client = get_client()
    if client is None:
        return None
    try:
        existing = [c.name for c in client.get_collections().collections]
        if collection_name not in existing:
            return None
        info = client.get_collection(collection_name)
        return {
            "points_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": info.status,
        }
    except Exception as e:
        log.error(f"Failed to get Qdrant collection info: {e}")
        return None