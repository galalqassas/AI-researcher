"""Tests for app.classification.classifier — cosine similarity, FTS sanitization, classification."""

import json
import struct
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.classification.classifier import (
    BUCKET_DESCRIPTIONS, _BUCKET_CACHE_VERSION,
    _sanitize_fts_query, cosine_similarity, classify_all_papers, compute_bucket_embeddings,
)
from app.database import Base
from app.models.paper import Paper


class TestCosineSimilarity:

    @pytest.mark.parametrize("a,b,expected", [
        (np.array([1, 2, 3], dtype=np.float32), np.array([1, 2, 3], dtype=np.float32), 1.0),
        (np.array([1, 0], dtype=np.float32), np.array([0, 1], dtype=np.float32), 0.0),
        (np.array([1, 2, 3], dtype=np.float32), np.array([0, 0, 0], dtype=np.float32), 0.0),
        (np.array([1, 0], dtype=np.float32), np.array([-1, 0], dtype=np.float32), -1.0),
    ])
    def test_vectors(self, a, b, expected):
        assert cosine_similarity(a, b) == pytest.approx(expected, abs=1e-6)


class TestSanitizeFtsQuery:

    @pytest.mark.parametrize("input_q,expected_substring", [
        ("deep learning AI", "deep OR learning OR AI"),
        ("AI AND NOT ML", "AI"),
        ("", ""),
    ])
    def test_basic_cases(self, input_q, expected_substring):
        result = _sanitize_fts_query(input_q)
        if expected_substring:
            assert expected_substring in result or result == expected_substring
        else:
            assert result == ""

    def test_strips_quoted_phrases(self):
        result = _sanitize_fts_query('"neural networks" deep')
        assert '"neural networks"' not in result
        assert "deep" in result

    def test_strips_operators(self):
        result = _sanitize_fts_query("AI AND NOT ML")
        assert "AND" not in result
        assert "NOT" not in result

    def test_special_chars_removed(self):
        result = _sanitize_fts_query("AI (machine-learning) +NLP")
        assert all(c not in result for c in "()+")


class TestComputeBucketEmbeddings:

    def test_cache_hit(self, tmp_path):
        cache_file = tmp_path / "bucket_embeddings.json"
        cache_file.write_text(json.dumps({"_version": _BUCKET_CACHE_VERSION, "general_ai": [0.1] * 768}))
        with patch("app.classification.classifier._bucket_cache_path", cache_file), \
             patch("app.classification.classifier.get_embedding") as mock_eg:
            result = compute_bucket_embeddings()
        mock_eg.assert_not_called()
        assert "general_ai" in result

    def test_cache_stale_recomputes(self, tmp_path):
        cache_file = tmp_path / "bucket_embeddings.json"
        cache_file.write_text(json.dumps({"_version": "old", "general_ai": [0.1] * 768}))
        mock_vec = np.array([0.2] * 768, dtype=np.float32)
        with patch("app.classification.classifier._bucket_cache_path", cache_file), \
             patch("app.classification.classifier.get_embedding", return_value=mock_vec):
            result = compute_bucket_embeddings()
        assert len(result) == len(BUCKET_DESCRIPTIONS)

    def test_embedding_failure_skips_bucket(self, tmp_path):
        cache_file = tmp_path / "bucket_embeddings.json"
        with patch("app.classification.classifier._bucket_cache_path", cache_file), \
             patch("app.classification.classifier.get_embedding", return_value=None):
            assert compute_bucket_embeddings() == {}


class TestClassifyAllPapers:

    @pytest.fixture
    def classify_engine(self):
        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(eng)
        with eng.connect() as conn:
            conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
            conn.commit()
        return eng

    @pytest.fixture
    def classify_session(self, classify_engine):
        session = sessionmaker(bind=classify_engine)()
        yield session
        session.close()

    def test_no_bucket_embeddings_returns_zero(self, classify_engine, classify_session):
        paper = Paper(arxiv_id="1", title="T", abstract="A", full_text="F",
                       ingested_at=datetime.now(timezone.utc), embedding=struct.pack("3f", 1, 0, 0))
        classify_session.add(paper)
        classify_session.commit()
        with patch("app.classification.classifier.compute_bucket_embeddings", return_value={}), \
             patch("app.classification.classifier.Session", return_value=classify_session):
            assert classify_all_papers() == 0

    def test_assigns_buckets_to_papers(self, classify_engine, classify_session):
        emb = np.array([0.1] * 768, dtype=np.float32)
        emb /= np.linalg.norm(emb)
        paper = Paper(arxiv_id="1", title="Deep Learning for NLP", abstract="DL",
                       full_text="F", ingested_at=datetime.now(timezone.utc), embedding=struct.pack(f"{len(emb)}f", *emb))
        classify_session.add(paper)
        classify_session.commit()

        bucket_embeds = {"general_ai": emb, "autonomous_agents": np.zeros(768, dtype=np.float32),
                         "ai_finance": np.zeros(768, dtype=np.float32)}
        with patch("app.classification.classifier.compute_bucket_embeddings", return_value=bucket_embeds), \
             patch("app.classification.classifier.Session", return_value=classify_session), \
             patch("app.classification.classifier._bm25_search", return_value=[]), \
             patch("app.classification.classifier.get_collection_info", return_value=None):
            assert classify_all_papers() == 1

        # Verify via raw SQL since classify_all_papers closes its session
        with classify_engine.connect() as conn:
            buckets = json.loads(conn.execute(text("SELECT buckets FROM papers")).fetchone()[0])
        assert "general_ai" in buckets