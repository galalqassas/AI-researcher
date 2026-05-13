import json
import logging
import re
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sqlalchemy import text
from app.config import SIMILARITY_THRESHOLD, RRF_K
from app.classification.embedder import get_embedding, bytes_to_embed
from app.classification.qdrant_store import get_collection_info
from app.database import Session, engine
from app.models.paper import Paper

log = logging.getLogger(__name__)

BUCKET_DESCRIPTIONS = {
    "general_ai": "artificial intelligence machine learning deep learning neural networks NLP computer vision transformer LLM foundation model",
    "autonomous_agents": "autonomous agents multi-agent systems agent planning tool use reasoning language agent agentic AI",
    "ai_finance": "AI in finance machine learning trading financial forecasting fintech risk management portfolio optimization algorithmic trading deep learning finance investment",
}

_bucket_cache_path = Path(__file__).resolve().parent.parent.parent / "data" / "bucket_embeddings.json"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def compute_bucket_embeddings() -> dict[str, np.ndarray]:
    """Pre-compute embedding for each bucket description (cached to disk)."""
    cache = {}
    if _bucket_cache_path.exists():
        try:
            raw = json.loads(_bucket_cache_path.read_text())
            cache = {k: np.array(v, dtype=np.float32) for k, v in raw.items()}
            log.info("Loaded bucket embeddings from cache")
            return cache
        except Exception:
            log.warning("Failed to load bucket embedding cache, recomputing")

    for bucket, desc in BUCKET_DESCRIPTIONS.items():
        vec = get_embedding(desc)
        if vec is not None:
            cache[bucket] = vec
        else:
            log.error(f"Failed to embed bucket: {bucket}")

    if cache:
        _bucket_cache_path.parent.mkdir(parents=True, exist_ok=True)
        _bucket_cache_path.write_text(json.dumps({k: v.tolist() for k, v in cache.items()}))
        log.info("Saved bucket embeddings to cache")

    return cache


def _sanitize_fts_query(query: str) -> str:
    """Convert a free-text query into a valid FTS5 MATCH expression.

    FTS5 MATCH uses implicit AND between terms (all terms must match).
    For BM25 search we want OR semantics so any term can match.
    We strip special characters, remove FTS5 operators, and join
    remaining words with OR.
    """
    # Remove FTS5 special operators ("OR", "AND", "NOT", "NEAR", column filters)
    cleaned = re.sub(r'"[^"]*"', '', query)  # remove quoted phrases
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)  # keep only word chars
    cleaned = re.sub(r'\b(AND|OR|NOT|NEAR)\b', '', cleaned, flags=re.IGNORECASE)
    # Split into words and join with OR for BM25 matching
    words = cleaned.split()
    return ' OR '.join(words) if words else ''


def _bm25_search(query: str, limit: int = 200) -> list[tuple[int, float]]:
    """Search papers_fts via BM25 and return (paper_id, score) pairs."""
    safe_query = _sanitize_fts_query(query)
    if not safe_query.strip():
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT rowid, bm25(papers_fts) AS score "
                    "FROM papers_fts WHERE papers_fts MATCH :q "
                    "ORDER BY score LIMIT :lim"
                ),
                {"q": safe_query, "lim": limit},
            ).fetchall()
            return [(row[0], float(row[1])) for row in rows]
    except Exception as e:
        log.warning(f"BM25 search failed: {e}")
        return []


def classify_all_papers():
    """Classify all embedded papers into research buckets using hybrid RRF."""
    session = Session()
    papers = session.query(Paper).filter(Paper.embedding != None).all()
    log.info(f"Classifying {len(papers)} papers")

    bucket_embeds = compute_bucket_embeddings()
    if not bucket_embeds:
        log.error("No bucket embeddings available — is Ollama running?")
        session.close()
        return 0

    qdrant_info = get_collection_info()
    qdrant_available = qdrant_info is not None and qdrant_info["points_count"] > 0
    if qdrant_available:
        log.info(f"Qdrant has {qdrant_info['points_count']} vectors indexed")

    # BM25 search per bucket description keywords for hybrid ranking
    bm25_per_bucket: dict[str, dict[int, float]] = {}
    paper_ids_in_bm25: set[int] = set()
    for bucket, desc in BUCKET_DESCRIPTIONS.items():
        hits = _bm25_search(desc, limit=200)
        bm25_per_bucket[bucket] = {pid: score for pid, score in hits}
        paper_ids_in_bm25.update(pid for pid, _ in hits)

    for paper in tqdm(papers, desc="Classifying"):
        if not paper.embedding:
            continue

        vec = bytes_to_embed(paper.embedding)

        # Dense scores (cosine similarity)
        dense_scores: dict[str, float] = {}
        for bucket, bucket_vec in bucket_embeds.items():
            dense_scores[bucket] = cosine_similarity(vec, bucket_vec)

        # Hybrid RRF fusion when BM25 data exists for this paper
        if paper.id in paper_ids_in_bm25:
            final_scores: dict[str, float] = {}
            for bucket in bucket_embeds:
                rrf_score = 0.0
                # Dense rank contribution
                ranked = sorted(dense_scores.items(), key=lambda x: x[1], reverse=True)
                for rank, (b, _) in enumerate(ranked):
                    if b == bucket:
                        rrf_score += 1.0 / (RRF_K + rank + 1)
                        break
                # BM25 rank contribution
                bucket_bm25 = bm25_per_bucket.get(bucket, {})
                if paper.id in bucket_bm25:
                    bm25_ranked = sorted(bucket_bm25.items(), key=lambda x: x[1], reverse=True)
                    for rank, (pid, _) in enumerate(bm25_ranked):
                        if pid == paper.id:
                            rrf_score += 1.0 / (RRF_K + rank + 1)
                            break
                final_scores[bucket] = rrf_score

            # Use dense threshold for primary assignment, RRF for fallback
            matched = [b for b, s in dense_scores.items() if s >= SIMILARITY_THRESHOLD]
            if not matched:
                matched = [max(final_scores, key=final_scores.get)]
        else:
            # Pure dense fallback (no BM25 data for this paper)
            matched = [b for b, s in dense_scores.items() if s >= SIMILARITY_THRESHOLD]
            if not matched:
                matched = [max(dense_scores, key=dense_scores.get)]

        paper.buckets = json.dumps(matched)
        log.debug(f"{paper.arxiv_id}: {matched}")

    session.commit()
    session.close()
    log.info("Classification complete")
    return len(papers)