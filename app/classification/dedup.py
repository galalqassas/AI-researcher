import logging
from rapidfuzz import fuzz
from app.database import Session
from app.models.paper import Paper
from app.config import DEDUP_THRESHOLD

log = logging.getLogger(__name__)


def find_duplicates(session=None) -> list[tuple[int, int, float]]:
    """Find duplicate papers by comparing titles using fuzzy matching.
    Returns list of (id1, id2, similarity_score) tuples."""
    if session is None:
        session = Session()

    papers = session.query(Paper).all()
    duplicates = []

    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            score = fuzz.ratio(papers[i].title.lower(), papers[j].title.lower()) / 100.0
            if score >= DEDUP_THRESHOLD:
                duplicates.append((papers[i].id, papers[j].id, score))

    return duplicates


def deduplicate(session=None) -> int:
    """Remove duplicate papers, keeping the one with more content (longer full_text).
    Returns number of papers removed."""
    if session is None:
        session = Session()

    duplicates = find_duplicates(session)
    removed = 0

    for id1, id2, score in duplicates:
        p1 = session.get(Paper, id1)
        p2 = session.get(Paper, id2)
        if not p1 or not p2:
            continue

        keep, drop = (p1, p2) if len(p1.full_text or "") >= len(p2.full_text or "") else (p2, p1)
        log.info(f"Duplicate (score={score:.2f}): keeping '{keep.title[:50]}', removing '{drop.title[:50]}'")
        session.delete(drop)
        removed += 1

    session.commit()
    return removed