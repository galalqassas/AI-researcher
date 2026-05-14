import logging
from rapidfuzz import fuzz
from tqdm import tqdm
from sqlalchemy import text
from app.database import get_session, engine
from app.models.paper import Paper
from app.config import DEDUP_THRESHOLD
from app.classification.pinecone_store import delete_points

log = logging.getLogger(__name__)


def find_duplicates(session, new_paper_ids: list[int] = None) -> list[tuple[int, int, float]]:
    """Find duplicate papers using fuzzy title matching.
    If new_paper_ids is given, only compare those papers against all others (O(n×m)).
    Otherwise, compare all pairs (O(n²) — use only for full scans)."""
    if new_paper_ids:
        # Incremental: compare new papers against all existing + each other
        new_papers = session.query(Paper).filter(Paper.id.in_(new_paper_ids)).all()
        existing = session.query(Paper).filter(Paper.id.notin_(new_paper_ids)).all()
        duplicates = []
        for np in tqdm(new_papers, desc="Finding duplicates (new)"):
            for ep in existing:
                score = fuzz.ratio(np.title.lower(), ep.title.lower()) / 100.0
                if score >= DEDUP_THRESHOLD:
                    duplicates.append((np.id, ep.id, score))
            # Also check new papers against each other
            for np2 in new_papers:
                if np.id < np2.id:
                    score = fuzz.ratio(np.title.lower(), np2.title.lower()) / 100.0
                    if score >= DEDUP_THRESHOLD:
                        duplicates.append((np.id, np2.id, score))
        return duplicates
    else:
        # Full scan: compare all pairs
        papers = session.query(Paper).all()
        duplicates = []
        for i in tqdm(range(len(papers)), desc="Finding duplicates"):
            for j in range(i + 1, len(papers)):
                score = fuzz.ratio(papers[i].title.lower(), papers[j].title.lower()) / 100.0
                if score >= DEDUP_THRESHOLD:
                    duplicates.append((papers[i].id, papers[j].id, score))
        return duplicates


def deduplicate(session=None, new_paper_ids: list[int] = None) -> int:
    """Remove duplicate papers, keeping the one with more content (longer full_text).
    Also removes orphan vectors from Pinecone and stale FTS rows.
    If new_paper_ids is given, only check those papers for duplicates (incremental).
    Returns number of papers removed."""
    if session is not None:
        return _deduplicate_core(session, new_paper_ids=new_paper_ids)

    with get_session() as session:
        return _deduplicate_core(session, new_paper_ids=new_paper_ids)


def _deduplicate_core(session, new_paper_ids: list[int] = None) -> int:
    duplicates = find_duplicates(session, new_paper_ids)
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