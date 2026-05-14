from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime, timezone
from app.database import Session, init_db
from app.models.paper import PipelineRun

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


def _mark_stale_runs_failed():
    """Mark any pipeline runs still in 'running' status as failed (server restarted mid-run)."""
    session = Session()
    try:
        stale = session.query(PipelineRun).filter(PipelineRun.status == "running").all()
        now = datetime.now(timezone.utc)
        for run in stale:
            run.status = "error"
            run.finished_at = now
            if run.started_at:
                # SQLite returns naive datetimes; make them UTC-aware
                started = run.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                run.duration_s = (now - started).total_seconds()
            run.error = "Pipeline interrupted — server restarted while run was in progress"
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def create_app() -> FastAPI:
    init_db()
    _mark_stale_runs_failed()

    app = FastAPI(title="Auto-Researcher", version="0.1.0")

    # CORS — allow frontend origins
    origins = [
        "https://ai-research-mvp.vercel.app",
        "http://localhost:5173",
        "https://dissuade-cadmium-wasting.ngrok-free.dev",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    from app.dashboard.routes import router
    app.include_router(router)

    # Serve React SPA in production (dashboard/dist/)
    if DASHBOARD_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=DASHBOARD_DIR / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve the React SPA. API routes are matched first; everything else falls through to index.html."""
            file_path = DASHBOARD_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(DASHBOARD_DIR / "index.html")

    return app


def _start_scheduler():
    """Start the background scheduler for auto-ingesting new papers."""
    from app.scheduler import start_scheduler
    start_scheduler()
