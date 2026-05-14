"""Tests for app.main — FastAPI app factory and startup logic."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.paper import PipelineRun
from app.main import _mark_stale_runs_failed, create_app


@pytest.fixture
def main_engine():
    """In-memory engine with tables + FTS5."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    return eng


class TestMarkStaleRunsFailed:

    def test_marks_running_as_error(self, main_engine):
        Session = sessionmaker(bind=main_engine)
        session = Session()

        run = PipelineRun(
            name="ingest",
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            status="running",
        )
        session.add(run)
        session.commit()
        run_id = run.id
        session.close()

        # Patch app.main.Session because _mark_stale_runs_failed imports
        # `from app.database import Session` (module-local binding).
        with patch("app.main.Session", Session), \
             patch("app.database.Session", Session):
            _mark_stale_runs_failed()

        session = Session()
        updated = session.get(PipelineRun, run_id)
        assert updated.status == "error"
        assert updated.finished_at is not None
        assert updated.duration_s >= 0
        assert "interrupted" in updated.error.lower()
        session.close()

    def test_leaves_non_running_untouched(self, main_engine):
        Session = sessionmaker(bind=main_engine)
        session = Session()

        run = PipelineRun(
            name="ingest",
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            status="success",
        )
        session.add(run)
        session.commit()
        run_id = run.id
        session.close()

        with patch("app.main.Session", Session), \
             patch("app.database.Session", Session):
            _mark_stale_runs_failed()

        session = Session()
        updated = session.get(PipelineRun, run_id)
        assert updated.status == "success"
        assert updated.finished_at is None
        assert updated.duration_s is None
        assert updated.error is None
        session.close()

    def test_rollback_on_exception(self, main_engine):
        """If DB operation fails, session is rolled back and closed."""
        mock_session = MagicMock()
        mock_session.query.side_effect = Exception("DB down")
        mock_session_cls = MagicMock(return_value=mock_session)

        with patch("app.main.Session", mock_session_cls):
            # Should not raise (exception is caught and logged)
            _mark_stale_runs_failed()
        # Verify rollback was called on the session object
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestCreateApp:

    def test_calls_init_db_and_mark_stale(self, main_engine):
        from app import database
        orig_engine = database.engine
        database.engine = main_engine
        try:
            with patch("app.main._mark_stale_runs_failed") as mock_mark:
                app = create_app()
            mock_mark.assert_called_once()
        finally:
            database.engine = orig_engine

    def test_includes_cors_middleware(self, main_engine):
        from app import database
        orig_engine = database.engine
        database.engine = main_engine
        try:
            app = create_app()
            # FastAPI user_middleware stores Middleware() wrapper objects;
            # the actual middleware class is in the .cls attribute.
            from fastapi.middleware.cors import CORSMiddleware
            middleware_classes = [m.cls for m in app.user_middleware]
            assert CORSMiddleware in middleware_classes
        finally:
            database.engine = orig_engine
