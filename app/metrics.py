"""Pipeline run tracking: duration, errors, stage results."""

import json
import logging
import time
from datetime import datetime, timezone
from contextlib import contextmanager
from app.database import Session
from app.models.paper import PipelineRun

log = logging.getLogger(__name__)


@contextmanager
def track_pipeline(name: str):
    """Context manager that tracks a pipeline run and saves results to DB.

    Usage:
        with track_pipeline("ingest") as ctx:
            added = run_ingestion()
            ctx["paper_count"] = added
            ctx["stages_json"] = {"ingested": added}
    """
    session = Session()
    run = PipelineRun(
        name=name,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    session.add(run)
    session.commit()
    run_id = run.id
    session.close()

    start = time.perf_counter()
    error_msg = None
    status = "success"
    ctx = {"paper_count": 0, "stages_json": {}}

    try:
        yield ctx
    except Exception as e:
        status = "error"
        error_msg = str(e)[:2000]
        log.error(f"Pipeline '{name}' failed: {e}")
        raise
    finally:
        duration = time.perf_counter() - start
        session = Session()
        try:
            run = session.get(PipelineRun, run_id)
            if run:
                run.finished_at = datetime.now(timezone.utc)
                run.status = status
                run.duration_s = round(duration, 2)
                run.error = error_msg
                run.paper_count = ctx.get("paper_count", 0)
                run.stages_json = json.dumps(ctx.get("stages_json", {}))
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    from app.alerts import send_alert
    send_alert(
        title=f"Pipeline {name} {status}",
        message=f"Duration: {duration:.1f}s | Papers: {ctx.get('paper_count', 0)}"
                + (f" | Error: {error_msg}" if error_msg else ""),
        status=status,
    )
    log.info(f"Pipeline '{name}' {status} in {duration:.1f}s")