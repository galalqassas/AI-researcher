from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.database import init_db

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Auto-Researcher", version="0.1.0")

    # CORS — allow all origins in dev; tighten for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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