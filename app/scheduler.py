"""Background scheduler: tries each bucket until a new paper is found, then processes it."""

import threading
import time
import logging

from app.config import BUCKETS

log = logging.getLogger(__name__)

_stop_event = threading.Event()


def _run_once():
    """Try each bucket until at least 1 new paper is found, then dedup/embed/classify it."""
    from app.ingestion.pipeline import run_ingestion, get_last_published_date
    from app.classification.dedup import deduplicate
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers
    from app.metrics import track_pipeline

    after_date = get_last_published_date()
    if after_date:
        log.info(f"Last published date in DB: {after_date}")

    with track_pipeline("scheduled_ingest") as ctx:
        for bucket in BUCKETS:
            added, new_ids = run_ingestion(
                max_results=3, bucket=bucket, sort_by_date=True, after_date=after_date
            )
            if added > 0:
                removed = deduplicate(new_paper_ids=new_ids)
                embedded = embed_all_papers()
                classified = classify_all_papers(paper_ids=new_ids)
                ctx["paper_count"] = added
                ctx["stages_json"] = {
                    "ingested": added,
                    "deduplicated": removed,
                    "embedded": embedded,
                    "classified": classified,
                }
                log.info(f"Ingested {added} new paper(s) from '{bucket}'")
                return
        ctx["paper_count"] = 0
        ctx["stages_json"] = {"status": "no_new_papers"}
        log.info("No new papers found in any bucket")


def _loop():
    """Background loop: try to ingest a new paper every 60 seconds."""
    while not _stop_event.is_set():
        try:
            _run_once()
        except Exception as e:
            log.error(f"Pipeline run failed: {e}")
        _stop_event.wait(60)


def start_scheduler():
    """Start the scheduler — tries all buckets per cycle until a new paper is found."""
    _stop_event.clear()
    thread = threading.Thread(target=_loop, daemon=True, name="paper-scheduler")
    thread.start()
    log.info("Scheduler started: tries each bucket per cycle, 60s interval")


def stop_scheduler():
    """Signal the scheduler to stop."""
    _stop_event.set()