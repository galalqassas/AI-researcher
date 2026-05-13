"""Tests for app.database — init_db, get_session, rebuild_fts."""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_session, init_db, rebuild_fts
from app.models.paper import Paper


@pytest.fixture
def db_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    yield eng
    eng.dispose()


def _mock_session_factory(engine):
    """Return a context manager that yields sessions bound to the given engine."""
    S = sessionmaker(bind=engine)

    @contextmanager
    def cm():
        s = S()
        try:
            yield s
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    return cm


class TestInitDb:

    def test_creates_tables(self, db_engine):
        with patch("app.database.engine", db_engine):
            init_db()

    def test_idempotent(self, db_engine):
        with patch("app.database.engine", db_engine):
            init_db()
            init_db()


class TestGetSession:

    def test_rollback_on_exception(self):
        eng = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(eng)
        S = sessionmaker(bind=eng)
        try:
            with patch("app.database.Session", S):
                with get_session() as session:
                    session.add(Paper(arxiv_id="t1", title="T", ingested_at=datetime.now(timezone.utc)))
                    raise ValueError("err")
        except ValueError:
            pass
        with S() as s:
            assert s.query(Paper).count() == 0
        eng.dispose()


class TestRebuildFts:

    def test_populates_fts(self, db_engine):
        S = sessionmaker(bind=db_engine)
        session = S()
        session.add(Paper(arxiv_id="1", title="Deep Learning for NLP",
                           abstract="Neural networks", ingested_at=datetime.now(timezone.utc)))
        session.commit()

        with patch("app.database.get_session", _mock_session_factory(db_engine)), \
             patch("app.database.engine", db_engine):
            rebuild_fts()

        with db_engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM papers_fts WHERE papers_fts MATCH 'deep'")).scalar() == 1
        session.close()

    def test_empty_db_no_error(self, db_engine):
        with patch("app.database.get_session", _mock_session_factory(db_engine)), \
             patch("app.database.engine", db_engine):
            rebuild_fts()  # should not raise