import struct
import logging
import numpy as np
from tqdm import tqdm
from app.config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL
from app.database import get_session
from app.models.paper import Paper
from app.classification.qdrant_store import upsert_papers_batch

log = logging.getLogger(__name__)

try:
    import ollama
    ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
except Exception as e:
    log.warning(f"Ollama client init failed: {e}")
    ollama_client = None


def get_embedding(text: str) -> np.ndarray | None:
    """Generate embedding for text using Ollama. Returns numpy array or None."""
    if not ollama_client:
        log.error("Ollama client not available")
        return None
    try:
        response = ollama_client.embed(model=OLLAMA_EMBED_MODEL, input=text)
        vec = response.embeddings[0]
        return np.array(vec, dtype=np.float32)
    except Exception as e:
        log.error(f"Embedding failed: {e}")
        return None


def embed_to_bytes(embedding: np.ndarray) -> bytes:
    """Serialize a numpy embedding to bytes for DB storage."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def bytes_to_embed(data: bytes) -> np.ndarray:
    """Deserialize bytes back to numpy embedding."""
    n = len(data) // 4
    return np.array(struct.unpack(f"{n}f", data), dtype=np.float32)


def embed_all_papers() -> int:
    """Generate and store embeddings for all papers that don't have one yet.

    Embeddings are stored both:
      - in the SQLite database (LargeBinary column) for backward compatibility
      - in the Qdrant vector database for similarity search

    Returns the number of papers successfully embedded (not including Qdrant failures).
    """
    with get_session() as session:
        papers = session.query(Paper).filter(Paper.embedding == None).all()
        log.info(f"Papers to embed: {len(papers)}")

        if not papers:
            return 0

        batch = []
        embedded_count = 0
        for paper in tqdm(papers, desc="Embedding"):
            text = f"{paper.title}. {paper.abstract or ''}"
            vec = get_embedding(text)
            if vec is not None:
                # Store in SQLite (backward-compatible)
                paper.embedding = embed_to_bytes(vec)
                embedded_count += 1

                # Collect for Qdrant batch upsert
                batch.append({
                    "id": paper.id,
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "embedding": vec,
                })

        # Commit to SQLite
        session.commit()

    # Batch upsert to Qdrant vector database
    if batch:
        try:
            upsert_papers_batch(batch)
            log.info(f"Stored {len(batch)} vectors in Qdrant")
        except Exception as e:
            log.error(f"Qdrant upsert failed (vectors still in SQLite): {e}")

    log.info(f"Embedded {embedded_count} papers")
    return embedded_count