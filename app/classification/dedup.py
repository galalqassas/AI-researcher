import logging
from rapidfuzz import fuzz
from tqdm import tqdm
from sqlalchemy import text
from app.database import get_session, engine
from app.models.paper import Paper
from app.config import DEDUP_THRESHOLD
from app.classification.pinecone_store import delete_points

log = logging.getLogger(__name__)


def find_duplicates(session) -> list[tuple[int, int, float]]:
    """Find duplicate papers by comparing titles using fuzzy matching.
    Returns list of (id1, id2, similarity_score) tuples."""
    papers = session.query(Paper).all()
    duplicates = []

    for i in tqdm(range(len(papers)), desc="Finding duplicates"):
        for j in range(i + 1, len(papers)):
            score = fuzz.ratio(papers[i].title.lower(), papers[j].title.lower()) / 100.0
            if score >= DEDUP_THRESHOLD:
                duplicates.append((papers[i].id, papers[j].id, score))

    return duplicates


def deduplicate(session=None) -> int:
    """Remove duplicate papers, keeping the one with more content (longer full_text).
    Also removes orphan vectors from Pinecone and stale FTS rows. Returns number of papers removed."""
    own_session = session is None
    if own_session:
        session = get_session()

    try:
        duplicates = find_duplicates(session)
        removed = 0
        orphan_ids = []

        for id1, id2, score in duplicates:
            p1 = session.get(Paper, id1)
            p2 = session.get(Paper, id2)
            if not p1 or not p2:
                continue

            keep, drop = (p1, p2) if len(p1.full_text or "") >= len(p2.full_text or "") else (p2, p1)
            log.info(f"Duplicate (score={score:.2f}): keeping '{keep.title[:50]}', removing '{drop.title[:50]}'")
            orphan_ids.append(drop.id)
            session.delete(drop)
            removed += 1

        session.commit()

        if orphan_ids:
            # Clean up FTS index for removed papers
            try:
                with engine.connect() as conn:
                    placeholders = ",".join(f":id{i}" for i in range(len(orphan_ids)))
                    params = {f"id{i}": pid for i, pid in enumerate(orphan_ids)}
                    conn.execute(text(f"DELETE FROM papers_fts WHERE rowid IN ({placeholders})"), params)
                    conn.commit()
            except Exception as e:
                log.warning(f"Failed to clean FTS index for {len(orphan_ids)} removed papers: {e}")

            # Clean up Pinecone vectors for removed papers
            try:
                delete_points(orphan_ids)
            except Exception as e:
                log.warning(f"Failed to delete {len(orphan_ids)} orphan vectors from Pinecone: {e}")

        return removed
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()