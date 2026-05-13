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
    QDRANT_GRPC_PORT,
    QDRANT_COLLECTION,
    QDRANT_EMBED_DIMENSION,
    OLLAMA_EMBED_MODEL,
)

log = logging.getLogger(__name__)

_qdrant_client: QdrantClient | None = None

try:
    # Prefer gRPC for better performance on large batch operations when available.
    # Falls back to REST-only if gRPC port is not configured.
    prefer_grpc = QDRANT_GRPC_PORT is not None
    _qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        grpc_port=QDRANT_GRPC_PORT if prefer_grpc else None,
        prefer_grpc=prefer_grpc,
    )
    log.info(f"Qdrant client initialized ({QDRANT_HOST}:{QDRANT_PORT}, grpc={prefer_grpc})")
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


def resync_embeddings():
    """Synchronize SQLite embeddings into Qdrant.

    Finds all papers that have embeddings in SQLite but are missing from
    Qdrant, and upserts them. Used to recover from dual-write drift.
    Returns the number of papers re-synced.
    """
    from app.database import Session
    from app.models.paper import Paper

    client = get_client()
    if client is None:
        log.error("Qdrant client not available — cannot resync")
        return 0

    ensure_collection()
    collection_info = get_collection_info()
    if collection_info is None:
        log.error("Could not get Qdrant collection info — cannot resync")
        return 0

    session = Session()
    try:
        papers_with_embeddings = session.query(Paper).filter(Paper.embedding != None).all()
        if not papers_with_embeddings:
            log.info("No papers with embeddings found in SQLite")
            return 0

        # Get existing point IDs from Qdrant
        existing_ids = set()
        offset = None
        while True:
            results, offset = client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            existing_ids.update(p.id for p in results)
            if offset is None:
                break

        # Find papers missing from Qdrant
        batch = []
        for paper in papers_with_embeddings:
            if paper.id not in existing_ids and paper.embedding is not None:
                vec = bytes_to_embed_local(paper.embedding)
                batch.append({
                    "id": paper.id,
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "embedding": vec,
                })

        if batch:
            upsert_papers_batch(batch)
            log.info(f"Re-synced {len(batch)} papers from SQLite to Qdrant")
        else:
            log.info("Qdrant is in sync — no papers to resync")

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