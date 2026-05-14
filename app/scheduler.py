"""Background scheduler: ingests new papers from arXiv on a configurable interval.

Uses a lookback window (default 3 days) to handle arXiv's 1-2 day publication lag.
Iterates all buckets per cycle, collects new paper IDs, then runs the pipeline once.
Fuzzy dedup is intentionally skipped — arxiv_id uniqueness in run_ingestion is
sufficient for incremental updates. Fuzzy dedup is available via the CLI for manual use.
"""

import threading
import logging
from datetime import date, timedelta

from app.config import BUCKETS, SCHEDULER_INTERVAL_SECONDS, SCHEDULER_LOOKBACK_DAYS, SCHEDULER_MAX_RESULTS

log = logging.getLogger(__name__)

_stop_event = threading.Event()
_lock = threading.Lock()


def _run_once():
    """Ingest new papers from all buckets, then embed and classify incrementally."""
    from app.ingestion.pipeline import run_ingestion
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers
    from app.metrics import track_pipeline

    after_date = date.today() - timedelta(days=SCHEDULER_LOOKBACK_DAYS)
    log.info(f"Scheduler: looking for papers since {after_date} (lookback={SCHEDULER_LOOKBACK_DAYS}d)")

    all_new_ids: list[int] = []
    per_bucket: dict[str, int] = {}

    with track_pipeline("scheduled_ingest") as ctx:
        for bucket in BUCKETS:
            try:
                added, new_ids = run_ingestion(
                    max_results=SCHEDULER_MAX_RESULTS,
                    bucket=bucket,
                    sort_by_date=True,
                    after_date=after_date,
                    silent=True,
                )
                all_new_ids.extend(new_ids or [])
                per_bucket[bucket] = added
                log.info(f"Scheduler: {bucket} — {added} new paper(s)")
            except Exception as e:
                log.error(f"Scheduler: error ingesting {bucket}: {e}")
                per_bucket[bucket] = 0

        total_added = sum(per_bucket.values())

        if not all_new_ids:
            ctx["paper_count"] = 0
            ctx["stages_json"] = {"status": "no_new_papers", **per_bucket}
            log.info("Scheduler: no new papers found")
            return

        # Incremental embed (only new papers) and classify
        embedded = embed_all_papers(paper_ids=all_new_ids)
        classified = classify_all_papers(paper_ids=all_new_ids)

        ctx["paper_count"] = total_added
        ctx["stages_json"] = {
            "ingested": total_added,
            "embedded": embedded,
            "classified": classified,
            **per_bucket,
        }
        log.info(f"Scheduler: ingested {total_added}, embedded {embedded}, classified {classified}")


def _loop():
    """Background loop: run _run_once at the configured interval."""
    while not _stop_event.is_set():
        if _lock.acquire(timeout=5):
            try:
                _run_once()
            except Exception as e:
                log.error(f"Scheduler cycle failed: {e}")
            finally:
                _lock.release()
        else:
            log.warning("Scheduler: previous cycle still running, skipping")

        _stop_event.wait(SCHEDULER_INTERVAL_SECONDS)


def start_scheduler():
    """Start the scheduler daemon thread."""
    _stop_event.clear()
    thread = threading.Thread(target=_loop, daemon=True, name="paper-scheduler")
    thread.start()
    log.info(
        f"Scheduler started: interval={SCHEDULER_INTERVAL_SECONDS}s, "
        f"lookback={SCHEDULER_LOOKBACK_DAYS}d, max_results={SCHEDULER_MAX_RESULTS}"
    )


def stop_scheduler():
    """Signal the scheduler to stop."""
    _stop_event.set()