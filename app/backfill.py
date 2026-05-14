import logging
from datetime import date, timedelta

from app.config import BUCKETS
from app.ingestion.pipeline import run_ingestion, get_last_published_date
from app.classification.dedup import deduplicate
from app.classification.embedder import embed_all_papers
from app.classification.classifier import classify_all_papers

log = logging.getLogger(__name__)


def run_backfill(days: int = 30, max_results_per_bucket: int = 100) -> dict:
    """Backfill papers from the last N days across all buckets.

    Ingests from all 3 buckets with a high max_results and an after_date filter,
    then runs incremental dedup/embed/classify once on all new papers.

    Returns a summary dict with counts per stage.
    """
    after_date = date.today() - timedelta(days=days)
    last_pub = get_last_published_date()
    if last_pub and last_pub > after_date:
        after_date = last_pub + timedelta(days=1)
        log.info(f"DB has papers up to {last_pub}, adjusting after_date to {after_date}")

    total_added = 0
    all_new_ids: list[int] = []
    per_bucket: dict[str, int] = {}

    for bucket in BUCKETS:
        added, new_ids = run_ingestion(
            max_results=max_results_per_bucket,
            bucket=bucket,
            sort_by_date=True,
            after_date=after_date,
        )
        total_added += added
        all_new_ids.extend(new_ids)
        per_bucket[bucket] = added
        log.info(f"Backfill '{bucket}': {added} new papers")

    if not all_new_ids:
        log.info("No new papers found during backfill")
        return {"ingested": 0, "per_bucket": per_bucket, "deduplicated": 0, "embedded": 0, "classified": 0}

    removed = deduplicate(new_paper_ids=all_new_ids)
    embedded = embed_all_papers(paper_ids=all_new_ids)
    classified = classify_all_papers(paper_ids=all_new_ids)

    log.info(f"Backfill complete: {total_added} ingested, {removed} deduped, {embedded} embedded, {classified} classified")
    return {
        "ingested": total_added,
        "per_bucket": per_bucket,
        "deduplicated": removed,
        "embedded": embedded,
        "classified": classified,
    }