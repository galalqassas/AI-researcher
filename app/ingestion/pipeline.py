import json
import logging
from datetime import datetime, date, timezone
from tqdm import tqdm
from app.config import BUCKETS
from app.database import get_session, init_db, engine
from app.models.paper import Paper
from app.ingestion.arxiv_client import fetch_papers
from app.ingestion.pdf_extractor import extract_paper_text
from sqlalchemy import text

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


def run_ingestion(query=None, max_results=None, bucket=None):
    """Full ingestion pipeline: fetch from arXiv → extract full text → store in DB.
    If bucket is specified, only fetch that bucket."""
    init_db()

    log.info("Starting ingestion pipeline...")
    papers = fetch_papers(max_results=max_results, query=query, bucket=bucket)

    if not papers:
        log.warning("No papers fetched from arXiv")
        return 0

    with get_session() as session:
        added = 0
        new_ids = []

        for p in tqdm(papers, desc="Storing papers"):
            existing = session.query(Paper).filter_by(arxiv_id=p["arxiv_id"]).first()
            if existing:
                log.debug(f"Already in DB: {p['arxiv_id']}")
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
            new_ids.append((paper.id, paper.title or "", paper.abstract or ""))
            added += 1

            if added % 10 == 0:
                session.commit()

        session.commit()

        # Update FTS index with new papers
        if new_ids:
            try:
                with engine.connect() as conn:
                    for pid, title, abstract in new_ids:
                        conn.execute(
                            text("INSERT OR REPLACE INTO papers_fts (rowid, title, abstract) VALUES (:id, :title, :abstract)"),
                            {"id": pid, "title": title, "abstract": abstract}
                        )
                    conn.commit()
            except Exception as e:
                log.warning(f"FTS index update failed: {e}")

    log.info(f"Ingestion complete: {added} new papers stored")
    return added