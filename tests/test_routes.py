"""Tests for app.dashboard.routes — FastAPI JSON API endpoints."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, Session
from app.models.paper import Paper, Report, PipelineRun


@pytest.fixture
def app_engine():
    """Shared in-memory engine with FTS5, initialized for the app."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    return eng


@pytest.fixture
def app_client(app_engine):
    """FastAPI TestClient with DB calls intercepted to use in-memory engine."""
    from app.main import create_app
    from app.database import init_db

    sf = sessionmaker(bind=app_engine)
    # Replace the module-level Session callable so every `Session()` returns a
    # session bound to our in-memory engine — works across threads.
    orig_call = Session.__call__
    Session.__call__ = lambda self, *a, **k: sf()
    try:
        with patch("app.database.engine", app_engine):
            init_db()
        app = create_app()
        yield TestClient(app)
    finally:
        Session.__call__ = orig_call


class TestAPIRoutes:

    def test_pipeline_runs_returns_json(self, app_client):
        resp = app_client.get("/pipeline-runs")
        assert resp.status_code == 200 and isinstance(resp.json(), list)

    def test_list_reports_returns_json(self, app_client):
        resp = app_client.get("/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_view_report_not_found(self, app_client):
        resp = app_client.get("/reports/9999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_search_returns_results(self, app_client):
        with patch("app.classification.embedder.get_embedding", return_value=None), \
             patch("app.classification.classifier._bm25_search", return_value=[]):
            resp = app_client.get("/search?q=test")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data and "query" in data

    def test_list_papers(self, app_engine):
        """GET /papers returns paginated paper listing."""
        sf = sessionmaker(bind=app_engine)
        s = sf()
        s.execute(text(
            "INSERT INTO papers (arxiv_id, title, authors, abstract, full_text, pdf_url, published_date, ingested_at, buckets) "
            "VALUES ('2401.00001', 'Test Paper', 'A', 'Abstract', 'Full', 'https://x', '2024-01-01', '2024-01-01', '[\"general_ai\"]')"
        ))
        s.commit()
        s.close()

        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.dashboard.routes.Session", sf):
                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.get("/papers")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["limit"] == 50
        assert len(data["results"]) == 1
        assert data["results"][0]["arxiv_id"] == "2401.00001"

    def test_list_papers_with_bucket_filter(self, app_engine):
        """GET /papers?bucket=general_ai filters by bucket."""
        sf = sessionmaker(bind=app_engine)
        s = sf()
        s.execute(text(
            "INSERT INTO papers (arxiv_id, title, authors, abstract, full_text, pdf_url, published_date, ingested_at, buckets) "
            "VALUES ('2401.00001', 'Test Paper', 'A', 'Abstract', 'Full', 'https://x', '2024-01-01', '2024-01-01', '[\"general_ai\"]')"
        ))
        s.commit()
        s.close()

        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.dashboard.routes.Session", sf):
                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.get("/papers?bucket=general_ai")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_papers_with_search(self, app_engine):
        """GET /papers?search= filters by title, abstract, arXiv ID, or authors."""
        sf = sessionmaker(bind=app_engine)
        s = sf()
        s.execute(text(
            "INSERT INTO papers (arxiv_id, title, authors, abstract, full_text, pdf_url, published_date, ingested_at, buckets) "
            "VALUES ('2401.00001', 'Alpha Paper', 'Smith', 'Abstract about cats', 'Full', 'https://x', '2024-01-01', '2024-01-01', '[\"general_ai\"]')"
        ))
        s.execute(text(
            "INSERT INTO papers (arxiv_id, title, authors, abstract, full_text, pdf_url, published_date, ingested_at, buckets) "
            "VALUES ('2401.00002', 'Beta Paper', 'Jones', 'Abstract about dogs', 'Full', 'https://x', '2024-01-01', '2024-01-01', '[\"ai_finance\"]')"
        ))
        s.commit()
        s.close()

        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.dashboard.routes.Session", sf):
                from app.main import create_app
                app = create_app()
                client = TestClient(app)

                resp = client.get("/papers?search=alpha")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 1
                assert data["results"][0]["arxiv_id"] == "2401.00001"

                resp = client.get("/papers?search=dogs")
                data = resp.json()
                assert data["total"] == 1
                assert data["results"][0]["arxiv_id"] == "2401.00002"

                resp = client.get("/papers?search=nonexistent")
                data = resp.json()
                assert data["total"] == 0
        finally:
            Session.__call__ = orig_call

    def test_list_papers_stats(self, app_engine):
        """GET /papers/stats returns total, today, per_bucket, per_date."""
        sf = sessionmaker(bind=app_engine)
        s = sf()
        s.execute(text(
            "INSERT INTO papers (arxiv_id, title, authors, abstract, full_text, pdf_url, published_date, ingested_at, buckets) "
            "VALUES ('2401.00001', 'Test Paper', 'A', 'Abstract', 'Full', 'https://x', '2024-01-01', datetime('now'), '[\"general_ai\"]')"
        ))
        s.commit()
        s.close()

        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.dashboard.routes.Session", sf):
                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.get("/papers/stats")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["today"] == 1
        assert data["per_bucket"]["general_ai"] == 1
        assert isinstance(data["per_date"], list)

    def test_trigger_ingest(self, app_engine):
        """POST /ingest runs pipeline stages and returns counts."""
        sf = sessionmaker(bind=app_engine)
        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.ingestion.pipeline.run_ingestion", return_value=(5, [1,2,3,4,5])) as mock_ingest, \
                 patch("app.classification.dedup.deduplicate", return_value=1) as mock_dedup, \
                 patch("app.classification.embedder.embed_all_papers", return_value=4) as mock_embed, \
                 patch("app.classification.classifier.classify_all_papers", return_value=4) as mock_classify, \
                 patch("app.metrics.track_pipeline") as mock_track:

                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value={})
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_track.return_value = mock_ctx

                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.post("/ingest")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["paper_count"] == 5

    def test_trigger_report(self, app_engine):
        """POST /reports/generate returns report id and paper count."""
        sf = sessionmaker(bind=app_engine)
        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.reports.generator.generate_report", return_value={"id": 1, "papers": 10}) as mock_gen, \
                 patch("app.metrics.track_pipeline") as mock_track:

                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value={})
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_track.return_value = mock_ctx

                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.post("/reports/generate?period=7d")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["period"] == "7d"
        assert data["paper_count"] == 10

    def test_trigger_report_error(self, app_engine):
        """POST /reports/generate returns 422 when report generation has an error."""
        sf = sessionmaker(bind=app_engine)
        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("app.reports.generator.generate_report", return_value={"error": "No papers found"}) as mock_gen, \
                 patch("app.metrics.track_pipeline") as mock_track:

                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value={})
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_track.return_value = mock_ctx

                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.post("/reports/generate?period=7d")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data

    def test_trigger_report_timeout(self, app_engine):
        """POST /reports/generate returns 504 on timeout."""
        import concurrent.futures
        sf = sessionmaker(bind=app_engine)
        orig_call = Session.__call__
        Session.__call__ = lambda self, *a, **k: sf()
        try:
            with patch("app.database.engine", app_engine), \
                 patch("concurrent.futures.ThreadPoolExecutor") as mock_executor, \
                 patch("app.metrics.track_pipeline") as mock_track:

                mock_future = MagicMock()
                mock_future.result.side_effect = concurrent.futures.TimeoutError()
                mock_exec = MagicMock()
                mock_exec.submit.return_value = mock_future
                mock_exec.__enter__ = MagicMock(return_value=mock_exec)
                mock_exec.__exit__ = MagicMock(return_value=False)
                mock_executor.return_value = mock_exec

                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value={})
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_track.return_value = mock_ctx

                from app.main import create_app
                app = create_app()
                client = TestClient(app)
                resp = client.post("/reports/generate?period=7d")
        finally:
            Session.__call__ = orig_call

        assert resp.status_code == 504
        data = resp.json()
        assert "error" in data
        assert "timeout" in data["error"].lower() or "exceeded" in data["error"].lower()
