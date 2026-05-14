"""Tests for app.metrics — track_pipeline context manager."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.paper import PipelineRun


@pytest.fixture
def metrics_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    return eng


@pytest.fixture
def metrics_session(metrics_engine):
    session = sessionmaker(bind=metrics_engine)()
    yield session
    session.close()


class TestTrackPipeline:

    def test_success_path(self, metrics_engine, metrics_session):
        with patch("app.metrics.Session", return_value=metrics_session), \
             patch("app.alerts.send_alert"):
            from app.metrics import track_pipeline
            with track_pipeline("ingest") as ctx:
                ctx["paper_count"] = 5

        run = metrics_session.query(PipelineRun).order_by(PipelineRun.id.desc()).first()
        assert run.name == "ingest" and run.status == "success"

    def test_error_path(self, metrics_engine, metrics_session):
        with patch("app.metrics.Session", return_value=metrics_session), \
             patch("app.alerts.send_alert"):
            from app.metrics import track_pipeline
            with pytest.raises(ValueError):
                with track_pipeline("report"):
                    raise ValueError("Report failed")

        run = metrics_session.query(PipelineRun).order_by(PipelineRun.id.desc()).first()
        assert run.status == "error" and "Report failed" in run.error