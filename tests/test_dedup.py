"""Tests for app.classification.dedup — fuzzy deduplication and cleanup."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.classification.dedup import find_duplicates, deduplicate
from app.database import Base
from app.models.paper import Paper


@pytest.fixture
def dedup_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
        conn.commit()
    return eng


@pytest.fixture
def dedup_session(dedup_engine):
    session = sessionmaker(bind=dedup_engine)()
    yield session
    session.close()


def _add_paper(session, arxiv_id, title, full_text="some content here", abstract="abstract"):
    p = Paper(arxiv_id=arxiv_id, title=title, full_text=full_text,
              abstract=abstract, ingested_at=datetime.now(timezone.utc))
    session.add(p)
    session.flush()
    return p


class TestFindDuplicates:

    def test_finds_similar_titles(self, dedup_session):
        _add_paper(dedup_session, "1", "Attention Is All You Need", full_text="a" * 500)
        _add_paper(dedup_session, "2", "Attention is all you need!", full_text="b" * 300)
        dedup_session.commit()
        dups = find_duplicates(dedup_session)
        assert len(dups) > 0 and all(s >= 0.85 for _, _, s in dups)

    def test_no_match_dissimilar(self, dedup_session):
        _add_paper(dedup_session, "1", "Attention Is All You Need")
        _add_paper(dedup_session, "2", "Deep Reinforcement Learning for Robotics")
        dedup_session.commit()
        assert find_duplicates(dedup_session) == []

    def test_empty_db(self, dedup_session):
        assert find_duplicates(dedup_session) == []


class TestDeduplicate:

    def test_keeps_paper_with_longer_text(self, dedup_engine, dedup_session):
        _add_paper(dedup_session, "1", "Attention Is All You Need", full_text="a" * 500)
        _add_paper(dedup_session, "2", "Attention is all you need!", full_text="b" * 100)
        dedup_session.commit()
        with patch("app.classification.dedup.engine", dedup_engine), \
             patch("app.classification.dedup.delete_points"):
            assert deduplicate(session=dedup_session) == 1
        remaining = dedup_session.query(Paper).all()
        assert len(remaining) == 1 and remaining[0].full_text == "a" * 500

    def test_none_full_text_treated_as_empty(self, dedup_engine, dedup_session):
        _add_paper(dedup_session, "1", "Attention Is All You Need", full_text=None)
        _add_paper(dedup_session, "2", "Attention is all you need!", full_text="content")
        dedup_session.commit()
        with patch("app.classification.dedup.engine", dedup_engine), \
             patch("app.classification.dedup.delete_points"):
            assert deduplicate(session=dedup_session) == 1

    def test_fts_cleanup_on_dedup(self, dedup_engine, dedup_session):
        p1 = _add_paper(dedup_session, "1", "Attention Is All You Need", full_text="a" * 500)
        p2 = _add_paper(dedup_session, "2", "Attention is all you need!", full_text="b" * 100)
        dedup_session.commit()

        with dedup_engine.connect() as conn:
            conn.execute(text("INSERT INTO papers_fts (rowid, title, abstract) VALUES (:id, :t, :a)"),
                         [{"id": p1.id, "t": p1.title, "a": "a1"}, {"id": p2.id, "t": p2.title, "a": "a2"}])
            conn.commit()

        with patch("app.classification.dedup.engine", dedup_engine), \
             patch("app.classification.dedup.delete_points"):
            assert deduplicate(session=dedup_session) == 1

        with dedup_engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM papers_fts")).scalar() == 1