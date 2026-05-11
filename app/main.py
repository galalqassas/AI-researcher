from fastapi import FastAPI
from app.database import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Auto-Researcher", version="0.1.0")
    from app.dashboard.routes import router
    app.include_router(router)
    return app