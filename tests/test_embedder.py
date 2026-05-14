"""Tests for app.classification.embedder — embedding serialization and Ollama calls."""

import struct
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.classification.embedder import bytes_to_embed, embed_all_papers, embed_to_bytes, get_embedding
from app.database import Base
from app.models.paper import Paper


class TestEmbedSerialization:

    def test_roundtrip(self):
        vec = np.array([0.1, -0.2, 0.3, 0.0, 1.0], dtype=np.float32)
        np.testing.assert_allclose(bytes_to_embed(embed_to_bytes(vec)), vec, atol=1e-6)

    def test_roundtrip_large_vector(self, sample_embedding):
        np.testing.assert_allclose(bytes_to_embed(embed_to_bytes(sample_embedding)), sample_embedding, atol=1e-6)

    def test_empty_array(self):
        assert embed_to_bytes(np.array([], dtype=np.float32)) == b""
        assert len(bytes_to_embed(b"")) == 0


class TestGetEmbedding:

    def test_success(self):
        mock_client = MagicMock()
        mock_client.embed.return_value = MagicMock(embeddings=[[0.1] * 768])
        with patch("app.classification.embedder.ollama_client", mock_client):
            result = get_embedding("text")
        assert result is not None and len(result) == 768

    def test_no_client(self):
        with patch("app.classification.embedder.ollama_client", None):
            assert get_embedding("text") is None

    def test_api_failure(self):
        mock_client = MagicMock()
        mock_client.embed.side_effect = Exception("Ollama unreachable")
        with patch("app.classification.embedder.ollama_client", mock_client):
            result = get_embedding("text")
        assert result is None


class TestEmbedAllPapers:

    @pytest.fixture
    def embed_session(self, db_engine, db_session):
        """Reuse shared db_engine/db_session fixtures from conftest."""
        return db_engine, db_session

    def test_embeds_unembedded_papers(self, db_engine, db_session):
        paper = Paper(arxiv_id="2401.00001", title="T", abstract="A", full_text="F",
                       ingested_at=datetime.now(timezone.utc), embedding=None)
        db_session.add(paper)
        db_session.commit()

        mock_emb = np.array([0.1] * 768, dtype=np.float32)
        with patch("app.classification.embedder.get_session") as mock_gs, \
             patch("app.classification.embedder.get_embedding", return_value=mock_emb), \
             patch("app.classification.embedder.upsert_papers_batch") as mock_upsert:
            mock_gs.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            assert embed_all_papers() == 1
        mock_upsert.assert_called_once()

    def test_skips_already_embedded(self, db_engine, db_session):
        paper = Paper(arxiv_id="2401.00001", title="T", abstract="A", full_text="F",
                       ingested_at=datetime.now(timezone.utc), embedding=struct.pack("3f", 1, 0, 0))
        db_session.add(paper)
        db_session.commit()

        with patch("app.classification.embedder.get_session") as mock_gs, \
             patch("app.classification.embedder.get_embedding") as mock_eg:
            mock_gs.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            assert embed_all_papers() == 0
        mock_eg.assert_not_called()

    def test_paper_ids_filters_to_specific_papers(self, db_engine, db_session):
        """When paper_ids is given, only embed those papers (incremental mode)."""
        p1 = Paper(arxiv_id="2401.00001", title="T1", abstract="A1", full_text="F",
                    ingested_at=datetime.now(timezone.utc), embedding=None)
        p2 = Paper(arxiv_id="2401.00002", title="T2", abstract="A2", full_text="F",
                    ingested_at=datetime.now(timezone.utc), embedding=None)
        db_session.add_all([p1, p2])
        db_session.commit()

        mock_emb = np.array([0.1] * 768, dtype=np.float32)
        with patch("app.classification.embedder.get_session") as mock_gs, \
             patch("app.classification.embedder.get_embedding", return_value=mock_emb), \
             patch("app.classification.embedder.upsert_papers_batch"):
            mock_gs.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_gs.return_value.__exit__ = MagicMock(return_value=False)
            # Only embed paper p1 (skip p2 which is also unembedded)
            assert embed_all_papers(paper_ids=[p1.id]) == 1