import json
import logging
import numpy as np
from app.config import BUCKETS, ARXIV_KEYWORDS, SIMILARITY_THRESHOLD
from app.classification.embedder import get_embedding, embed_to_bytes, bytes_to_embed
from app.database import Session
from app.models.paper import Paper

log = logging.getLogger(__name__)

BUCKET_DESCRIPTIONS = {
    "general_ai": "artificial intelligence machine learning deep learning neural networks NLP computer vision transformer LLM foundation model",
    "autonomous_agents": "autonomous agents multi-agent systems agent planning tool use reasoning language agent agentic AI",
    "ai_finance": "AI in finance machine learning trading financial forecasting fintech risk management portfolio optimization algorithmic trading deep learning finance investment",
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def compute_bucket_embeddings() -> dict[str, np.ndarray]:
    """Pre-compute embedding for each bucket description."""
    bucket_embeds = {}
    for bucket, desc in BUCKET_DESCRIPTIONS.items():
        vec = get_embedding(desc)
        if vec is not None:
            bucket_embeds[bucket] = vec
        else:
            log.error(f"Failed to embed bucket: {bucket}")
    return bucket_embeds


def classify_all_papers():
    """Classify all embedded papers into research buckets using cosine similarity."""
    session = Session()
    papers = session.query(Paper).filter(Paper.embedding != None).all()
    log.info(f"Classifying {len(papers)} papers")

    bucket_embeds = compute_bucket_embeddings()
    if not bucket_embeds:
        log.error("No bucket embeddings available — is Ollama running?")
        session.close()
        return

    for paper in papers:
        if not paper.embedding:
            continue
        vec = bytes_to_embed(paper.embedding)

        matched = []
        for bucket, bucket_vec in bucket_embeds.items():
            score = cosine_similarity(vec, bucket_vec)
            if score >= SIMILARITY_THRESHOLD:
                matched.append(bucket)

        if not matched:
            scores = {b: cosine_similarity(vec, bv) for b, bv in bucket_embeds.items()}
            matched = [max(scores, key=scores.get)]

        paper.buckets = json.dumps(matched)
        log.debug(f"{paper.arxiv_id}: {matched}")

    session.commit()
    session.close()
    log.info("Classification complete")