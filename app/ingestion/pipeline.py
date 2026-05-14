import json
import logging
from datetime import datetime, date, timezone
from tqdm import tqdm
from app.database import get_session, init_db, engine
from app.models.paper import Paper
from app.ingestion.arxiv_client import fetch_papers
from app.ingestion.pdf_extractor import extract_paper_text
from sqlalchemy import func, text

log = logging.getLogger(__name__)


def parse_published_date(value) -> date | None:
    """Parse a date string (YYYY-MM-DD) into a date object."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def get_last_published_date() -> date | None:
    """Return the most recent published_date in the DB, or None if empty."""
    init_db()
    with get_session() as session:
        result = session.query(func.max(Paper.published_date)).scalar()
        return result


def run_ingestion(query=None, max_results=None, bucket=None, sort_by_date=False, after_date=None, before_date=None, silent=False):
    """Full ingestion pipeline: fetch from arXiv → extract full text → store in DB.
    If bucket is specified, only fetch that bucket.
    sort_by_date: Sort by newest first instead of relevance (for scheduler).
    after_date: If set, only fetch papers published on or after this date (server-side filter).
    before_date: If set, only fetch papers published before this date (server-side filter).
    silent: If True, suppress progress bars (for background scheduler).
    Returns (count, new_ids) — number of new papers and their DB IDs."""
    init_db()

    log.info("Starting ingestion pipeline...")
    papers = fetch_papers(max_results=max_results, query=query, bucket=bucket,
                          sort_by_date=sort_by_date, after_date=after_date, before_date=before_date,
                          silent=silent)

    if not papers:
        log.warning("No papers fetched from arXiv")
        return 0, []

    with get_session() as session:
        added = 0
        skipped = 0
        new_rows = []  # [(id, title, abstract)] for FTS index
        new_ids = []   # [id] for downstream dedup/classify

        paper_iter = papers if silent else tqdm(papers, desc="Storing papers")
        for p in paper_iter:
            existing = session.query(Paper).filter_by(arxiv_id=p["arxiv_id"]).first()
            if existing:
                skipped += 1
                continue

            full_text = extract_paper_text(p["arxiv_id"], p.get("pdf_url", ""))

            paper = Paper(
                arxiv_id=p["arxiv_id"],
                title=p["title"],
                authors=p.get("authors", ""),
                abstract=p.get("abstract", ""),
                full_text=full_text or "",
                pdf_url=p.get("pdf_url", ""),
                published_date=parse_published_date(p.get("published_date")),
                ingested_at=datetime.now(timezone.utc),
                buckets=json.dumps(p.get("buckets", [])),
            )
            session.add(paper)
            session.flush()  # assign ID before FTS
            new_rows.append((paper.id, paper.title or "", paper.abstract or ""))
            new_ids.append(paper.id)
            added += 1

            if added % 10 == 0:
                session.commit()

        session.commit()

        # Update FTS index with new papers
        if new_rows:
            try:
                with engine.connect() as conn:
                    for pid, title, abstract in new_rows:
                        conn.execute(
                            text("INSERT OR REPLACE INTO papers_fts (rowid, title, abstract) VALUES (:id, :title, :abstract)"),
                            {"id": pid, "title": title, "abstract": abstract}
                        )
                    conn.commit()
            except Exception as e:
                log.warning(f"FTS index update failed: {e}")

    log.info(f"Ingestion complete: {added} new papers stored ({skipped} already in DB, {len(papers)} checked)")
    return added, new_ids