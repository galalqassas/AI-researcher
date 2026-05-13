"""Tests for app.ingestion.pipeline — date parsing and ingestion flow."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.ingestion.pipeline import parse_published_date, run_ingestion
from app.models.paper import Paper


@pytest.fixture
def pipeline_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    return eng


@pytest.fixture
def pipeline_session(pipeline_engine):
    session = sessionmaker(bind=pipeline_engine)()
    yield session
    session.close()


class TestParsePublishedDate:

    @pytest.mark.parametrize("input_val,expected", [
        ("2024-01-15", date(2024, 1, 15)),
        (date(2024, 6, 1), date(2024, 6, 1)),
        (None, None),
        ("not-a-date", None),
        ("", None),
        ("15/01/2024", None),
    ])
    def test_various_inputs(self, input_val, expected):
        assert parse_published_date(input_val) == expected


class TestRunIngestion:

    def test_stores_papers(self, pipeline_engine, pipeline_session):
        mock_papers = [{"arxiv_id": "2401.00001", "title": "Test Paper One",
                         "authors": "A", "abstract": "Abs", "pdf_url": "https://x",
                         "published_date": "2024-01-15", "buckets": ["general_ai"]}]
        with patch("app.ingestion.pipeline.fetch_papers", return_value=mock_papers), \
             patch("app.ingestion.pipeline.extract_paper_text", return_value="text"), \
             patch("app.ingestion.pipeline.init_db"), \
             patch("app.ingestion.pipeline.get_session") as mock_gs, \
             patch("app.ingestion.pipeline.engine", pipeline_engine):
            mock_gs.return_value.__enter__ = MagicMock(return_value=pipeline_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            added = run_ingestion()
        assert added == 1
        assert pipeline_session.query(Paper).count() == 1

    def test_duplicate_skipped(self, pipeline_engine, pipeline_session):
        paper = [{"arxiv_id": "2401.00001", "title": "P1", "authors": "A",
                   "abstract": "X", "pdf_url": "https://x", "published_date": "2024-01-15",
                   "buckets": ["general_ai"]}]
        with patch("app.ingestion.pipeline.fetch_papers", return_value=paper), \
             patch("app.ingestion.pipeline.extract_paper_text", return_value="text"), \
             patch("app.ingestion.pipeline.init_db"), \
             patch("app.ingestion.pipeline.get_session") as mock_gs, \
             patch("app.ingestion.pipeline.engine", pipeline_engine):
            mock_gs.return_value.__enter__ = MagicMock(return_value=pipeline_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            assert run_ingestion() == 1
        # Second run with same paper
        with patch("app.ingestion.pipeline.fetch_papers", return_value=paper), \
             patch("app.ingestion.pipeline.extract_paper_text", return_value="text"), \
             patch("app.ingestion.pipeline.init_db"), \
             patch("app.ingestion.pipeline.get_session") as mock_gs, \
             patch("app.ingestion.pipeline.engine", pipeline_engine):
            mock_gs.return_value.__enter__ = MagicMock(return_value=pipeline_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            assert run_ingestion() == 0

    def test_no_papers_returns_zero(self, pipeline_engine, pipeline_session):
        with patch("app.ingestion.pipeline.fetch_papers", return_value=[]), \
             patch("app.ingestion.pipeline.init_db"), \
             patch("app.ingestion.pipeline.get_session") as mock_gs:
            mock_gs.return_value.__enter__ = MagicMock(return_value=pipeline_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            assert run_ingestion() == 0