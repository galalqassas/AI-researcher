import json
import logging
import re
import hashlib
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sqlalchemy import text
from app.config import SIMILARITY_THRESHOLD, RRF_K, RERANK_MARGIN, RERANK_WEIGHT_COSINE, RERANK_WEIGHT_BM25
from app.classification.embedder import get_embedding, bytes_to_embed
from app.classification.pinecone_store import get_collection_info
from app.database import engine, Session
from app.models.paper import Paper

log = logging.getLogger(__name__)

BUCKET_DESCRIPTIONS = {
    "general_ai": "artificial intelligence machine learning deep learning neural networks NLP computer vision transformer LLM foundation model",
    "autonomous_agents": "autonomous agents multi-agent systems agent planning tool use reasoning language agent agentic AI",
    "ai_finance": "AI in finance machine learning trading financial forecasting fintech risk management portfolio optimization algorithmic trading deep learning finance investment",
}

_BUCKET_CACHE_VERSION = hashlib.sha256(
    json.dumps(BUCKET_DESCRIPTIONS, sort_keys=True).encode()
).hexdigest()[:16]

_bucket_cache_path = Path(__file__).resolve().parent.parent.parent / "data" / "bucket_embeddings.json"


def compute_bucket_embeddings() -> dict[str, np.ndarray]:
    """Pre-compute embedding for each bucket description (cached to disk).

    Cache is invalidated automatically when BUCKET_DESCRIPTIONS changes
    by comparing a SHA-256 fingerprint of the descriptions dict.
    """
    if _bucket_cache_path.exists():
        try:
            raw = json.loads(_bucket_cache_path.read_text())
            # Check cache version — invalidate if descriptions changed
            cached_version = raw.get("_version")
            if cached_version == _BUCKET_CACHE_VERSION:
                cache = {k: np.array(v, dtype=np.float32) for k, v in raw.items() if k != "_version"}
                log.info("Loaded bucket embeddings from cache (version match)")
                return cache
            else:
                log.info("Bucket descriptions changed — invalidating embedding cache")
        except Exception:
            log.warning("Failed to load bucket embedding cache, recomputing")

    cache = {}
    for bucket, desc in BUCKET_DESCRIPTIONS.items():
        vec = get_embedding(desc)
        if vec is not None:
            cache[bucket] = vec
        else:
            log.error(f"Failed to embed bucket: {bucket}")

    if cache:
        _bucket_cache_path.parent.mkdir(parents=True, exist_ok=True)
        # Save cache with version fingerprint
        cache_data = {k: v.tolist() for k, v in cache.items()}
        cache_data["_version"] = _BUCKET_CACHE_VERSION
        _bucket_cache_path.write_text(json.dumps(cache_data))
        log.info("Saved bucket embeddings to cache")

    return cache


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


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


def classify_all_papers(paper_ids: list[int] = None):
    """Classify papers into research buckets using hybrid RRF.
    If paper_ids is given, only classify those papers (incremental).
    Otherwise, classify all embedded papers (full scan)."""
    session = Session()
    query = session.query(Paper).filter(Paper.embedding != None)
    if paper_ids is not None:
        query = query.filter(Paper.id.in_(paper_ids))
    papers = query.all()
    log.info(f"Classifying {len(papers)} papers")

    bucket_embeds = compute_bucket_embeddings()
    if not bucket_embeds:
        log.error("No bucket embeddings available — is Ollama running?")
        session.close()
        return 0

    pinecone_info = get_collection_info()
    pinecone_available = pinecone_info is not None and pinecone_info["points_count"] > 0
    if pinecone_available:
        log.info(f"Pinecone has {pinecone_info['points_count']} vectors indexed")

    # BM25 search per bucket description keywords for hybrid ranking
    bm25_rank_per_bucket: dict[str, dict[int, int]] = {}
    paper_ids_in_bm25: set[int] = set()
    for bucket, desc in BUCKET_DESCRIPTIONS.items():
        hits = _bm25_search(desc, limit=200)
        sorted_hits = sorted(hits, key=lambda x: x[1])
        bm25_rank_per_bucket[bucket] = {pid: rank for rank, (pid, _) in enumerate(sorted_hits)}
        paper_ids_in_bm25.update(pid for pid, _ in hits)

    try:
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
                dense_ranked = sorted(dense_scores.items(), key=lambda x: x[1], reverse=True)
                dense_rank_map = {b: rank for rank, (b, _) in enumerate(dense_ranked)}

                for bucket in bucket_embeds:
                    rrf_score = 0.0
                    if bucket in dense_rank_map:
                        rrf_score += 1.0 / (RRF_K + dense_rank_map[bucket] + 1)
                    bucket_bm25_ranks = bm25_rank_per_bucket.get(bucket, {})
                    if paper.id in bucket_bm25_ranks:
                        rrf_score += 1.0 / (RRF_K + bucket_bm25_ranks[paper.id] + 1)
                    final_scores[bucket] = rrf_score

                matched = [b for b, s in dense_scores.items() if s >= SIMILARITY_THRESHOLD]
                borderline = [b for b, s in dense_scores.items()
                              if SIMILARITY_THRESHOLD - RERANK_MARGIN <= s < SIMILARITY_THRESHOLD]
                if borderline and final_scores:
                    for b in borderline:
                        cos_score = dense_scores.get(b, 0)
                        bm25_rank_score = final_scores.get(b, 0)
                        blended = RERANK_WEIGHT_COSINE * cos_score + RERANK_WEIGHT_BM25 * bm25_rank_score
                        if blended >= SIMILARITY_THRESHOLD * 0.8 and b not in matched:
                            matched.append(b)
                            log.debug(f"Reranked {paper.arxiv_id} into {b}: cosine={cos_score:.3f} rrf={bm25_rank_score:.4f} blended={blended:.4f}")
                if not matched:
                    matched = [max(final_scores, key=final_scores.get)]
            else:
                matched = [b for b, s in dense_scores.items() if s >= SIMILARITY_THRESHOLD]
                if not matched:
                    matched = [max(dense_scores, key=dense_scores.get)]

            paper.buckets = json.dumps(matched)
            log.debug(f"{paper.arxiv_id}: {matched}")

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    log.info("Classification complete")
    return len(papers)