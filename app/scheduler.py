"""Background scheduler: ingest papers from arXiv with incremental pipeline processing."""

import itertools
import threading
import time
import logging

from app.config import BUCKETS

log = logging.getLogger(__name__)

_bucket_cycle = itertools.cycle(BUCKETS)
_stop_event = threading.Event()


def _run_once():
    """Fetch newest papers from the next bucket, then dedup/embed/classify only new ones."""
    from app.ingestion.pipeline import run_ingestion
    from app.classification.dedup import deduplicate
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers
    from app.metrics import track_pipeline

    bucket = next(_bucket_cycle)
    with track_pipeline("scheduled_ingest") as ctx:
        added, new_ids = run_ingestion(max_results=2, bucket=bucket, sort_by_date=True)
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
            log.info(f"Pipeline complete for '{bucket}': {added} new paper(s)")
        else:
            ctx["paper_count"] = 0
            ctx["stages_json"] = {"status": "no_new_papers"}


def _loop():
    """Background loop: ingest and process papers every 60 seconds."""
    while not _stop_event.is_set():
        try:
            _run_once()
        except Exception as e:
            log.error(f"Pipeline run failed: {e}")
        _stop_event.wait(60)


def start_scheduler():
    """Start the scheduler — runs forever until stop() is called or process exits."""
    _stop_event.clear()
    thread = threading.Thread(target=_loop, daemon=True, name="paper-scheduler")
    thread.start()
    log.info("Scheduler started: 2 papers/min, incremental pipeline, rotating buckets")


def stop_scheduler():
    """Signal the scheduler to stop."""
    _stop_event.set()