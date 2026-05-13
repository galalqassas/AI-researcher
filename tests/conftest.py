"""Shared fixtures for Auto-Researcher tests.

Uses in-memory SQLite with FTS5 for DB-dependent tests.
External services (Ollama, Qdrant, arXiv, HTTP) are mocked per-test.
"""

import json
import struct
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import numpy as np
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.paper import Paper, Report, PipelineRun


# ---------------------------------------------------------------------------
# Shared DB engine + session fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_engine():
    """In-memory SQLite engine with all tables + FTS5.

    Uses check_same_thread=False for compatibility with FastAPI TestClient.
    """
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"
        ))
        conn.commit()
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(db_engine):
    """Yield a DB session, rolling back after each test for isolation."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# Paper factory fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def make_paper(db_session):
    """Insert a Paper and return it. Overrides accepted via kwargs."""
    _counter = 0

    def _make(**overrides):
        nonlocal _counter
        _counter += 1
        defaults = {
            "arxiv_id": f"2401.{_counter:05d}",
            "title": f"Test Paper {_counter}",
            "authors": "Author, Test",
            "abstract": "This is a test abstract for testing purposes.",
            "full_text": "Full text content " * 50,
            "pdf_url": f"https://arxiv.org/pdf/2401.{_counter:05d}",
            "published_date": date(2024, 1, 1),
            "ingested_at": datetime.now(timezone.utc),
            "buckets": json.dumps(["general_ai"]),
        }
        defaults.update(overrides)
        paper = Paper(**defaults)
        db_session.add(paper)
        db_session.commit()
        return paper

    return _make


# ---------------------------------------------------------------------------
# Embedding fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_embedding():
    """Deterministic normalized 768-dim embedding vector."""
    rng = np.random.RandomState(42)
    vec = rng.randn(768).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec


@pytest.fixture
def sample_embedding_bytes(sample_embedding):
    """Sample embedding serialized to bytes (for DB LargeBinary column)."""
    return struct.pack(f"{len(sample_embedding)}f", *sample_embedding)