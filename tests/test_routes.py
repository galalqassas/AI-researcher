"""Tests for app.dashboard.routes — FastAPI endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, Session as DBSession
from app.models.paper import Paper, Report, PipelineRun


@pytest.fixture
def app_engine():
    """Shared in-memory engine with FTS5, initialized for the app."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    return eng


@pytest.fixture
def app_client(app_engine):
    """FastAPI TestClient with patched DB."""
    from app.main import create_app
    from app.database import init_db

    with patch("app.database.engine", app_engine):
        init_db()

    app = create_app()
    sf = sessionmaker(bind=app_engine)
    with patch.object(DBSession, "__call__", side_effect=lambda: sf()):
        yield TestClient(app)


class TestDashboardRoutes:

    def test_dashboard_ok(self, app_client):
        assert app_client.get("/", follow_redirects=False).status_code == 200

    def test_pipeline_runs_returns_json(self, app_client, app_engine):
        with patch.object(DBSession, "__call__", side_effect=lambda: sessionmaker(bind=app_engine)()):
            from app.main import create_app
            tc = TestClient(create_app())
        resp = app_client.get("/pipeline-runs")
        assert resp.status_code == 200 and isinstance(resp.json(), list)

    def test_list_reports(self, app_client):
        assert app_client.get("/reports", follow_redirects=False).status_code == 200

    def test_view_report_not_found(self, app_client):
        resp = app_client.get("/reports/9999", follow_redirects=False)
        assert resp.status_code == 303 and resp.headers["location"] == "/"

    def test_search_returns_results(self, app_client):
        with patch("app.classification.embedder.get_embedding", return_value=None), \
             patch("app.classification.classifier._bm25_search", return_value=[]):
            resp = app_client.get("/search?q=test")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data and "query" in data