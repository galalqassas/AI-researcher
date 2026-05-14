"""Tests for app.classification.pinecone_store — Pinecone SDK wrapper functions."""

import struct
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.classification.pinecone_store import (
    bytes_to_embed_local,
    delete_points,
    ensure_collection,
    get_client,
    get_collection_info,
    get_index,
    resync_embeddings,
    search_similar,
    upsert_papers_batch,
)


class TestGetClient:

    def test_returns_singleton(self):
        """get_client returns the module-level _pc_client."""
        with patch("app.classification.pinecone_store._pc_client", "fake_client"):
            assert get_client() == "fake_client"

    def test_returns_none_when_unavailable(self):
        with patch("app.classification.pinecone_store._pc_client", None):
            assert get_client() is None


class TestGetIndex:

    def test_with_client(self):
        mock_client = MagicMock()
        mock_client.Index.return_value = "mock_index"
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client):
            assert get_index("test-index") == "mock_index"
            mock_client.Index.assert_called_once_with("test-index")

    def test_without_client(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            assert get_index("test-index") is None


class TestEnsureCollection:

    def test_skips_when_exists(self):
        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_index.name = "existing-index"
        mock_client.list_indexes.return_value = [mock_index]
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client):
            ensure_collection("existing-index")
        mock_client.create_index.assert_not_called()

    def test_creates_when_missing(self):
        mock_client = MagicMock()
        mock_client.list_indexes.return_value = []
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client), \
             patch("app.classification.pinecone_store.PINECONE_EMBED_DIMENSION", 768):
            ensure_collection("new-index")
        mock_client.create_index.assert_called_once()
        call_kwargs = mock_client.create_index.call_args.kwargs
        assert call_kwargs["name"] == "new-index"
        assert call_kwargs["dimension"] == 768
        assert call_kwargs["metric"] == "cosine"

    def test_noop_without_client(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            ensure_collection("any-index")  # should not raise


class TestUpsertPapersBatch:

    def test_upserts_normally(self):
        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client), \
             patch("app.classification.pinecone_store.ensure_collection"):
            papers = [
                {"id": 1, "arxiv_id": "a1", "title": "T1", "embedding": np.array([0.1, 0.2])},
                {"id": 2, "arxiv_id": "a2", "title": "T2", "embedding": np.array([0.3, 0.4])},
            ]
            upsert_papers_batch(papers, "test-index")
        mock_index.upsert.assert_called_once()
        vectors = mock_index.upsert.call_args.kwargs["vectors"]
        assert len(vectors) == 2
        assert vectors[0]["id"] == "1"
        assert vectors[0]["values"] == [0.1, 0.2]

    def test_empty_list_returns_early(self):
        with patch("app.classification.pinecone_store.get_client") as mock_gc:
            upsert_papers_batch([])
            mock_gc.assert_not_called()

    def test_no_client_logs_error(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            upsert_papers_batch([{"id": 1, "arxiv_id": "a1", "title": "T", "embedding": np.array([0.1])}])


class TestSearchSimilar:

    def test_returns_results(self):
        mock_hit = MagicMock()
        mock_hit.id = "42"
        mock_hit.score = 0.95
        mock_hit.metadata = {"arxiv_id": "x"}
        mock_index = MagicMock()
        mock_index.query.return_value = {"matches": [mock_hit]}
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client):
            results = search_similar(np.array([0.1, 0.2]), limit=5, collection_name="idx")
        assert len(results) == 1
        assert results[0]["id"] == 42
        assert results[0]["score"] == 0.95
        assert results[0]["payload"]["arxiv_id"] == "x"

    def test_no_client_returns_empty(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            assert search_similar(np.array([0.1])) == []


class TestDeletePoints:

    def test_deletes_normally(self):
        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client):
            delete_points([1, 2, 3], "idx")
        mock_index.delete.assert_called_once_with(ids=["1", "2", "3"])

    def test_no_client_returns_early(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            delete_points([1])  # should not raise


class TestGetCollectionInfo:

    def test_success(self):
        mock_stats = MagicMock()
        mock_stats.total_vector_count = 100
        mock_index = MagicMock()
        mock_index.describe_index_stats.return_value = mock_stats
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client):
            info = get_collection_info("idx")
        assert info["points_count"] == 100
        assert info["status"] == "ready"

    def test_error_returns_none(self):
        mock_index = MagicMock()
        mock_index.describe_index_stats.side_effect = Exception("down")
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client):
            assert get_collection_info("idx") is None

    def test_no_client_returns_none(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            assert get_collection_info("idx") is None


class TestResyncEmbeddings:

    def test_resyncs_missing_papers(self):
        """Only papers not already in Pinecone get upserted."""
        from app.models.paper import Paper

        emb = np.array([0.1, 0.2], dtype=np.float32)
        paper = Paper(
            id=1,
            arxiv_id="2401.00001",
            title="T",
            embedding=struct.pack("2f", 0.1, 0.2),
        )

        mock_fetch = MagicMock()
        mock_fetch.get.return_value = {}  # No existing vectors

        mock_index = MagicMock()
        mock_index.fetch.return_value = mock_fetch

        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [paper]

        with patch("app.classification.pinecone_store.get_client", return_value=mock_client), \
             patch("app.classification.pinecone_store.ensure_collection"), \
             patch("app.classification.pinecone_store.get_collection_info", return_value={"status": "ready"}), \
             patch("app.database.Session", return_value=mock_session), \
             patch("app.classification.pinecone_store.upsert_papers_batch") as mock_upsert:

            count = resync_embeddings()

        assert count == 1
        mock_upsert.assert_called_once()

    def test_no_client_returns_zero(self):
        with patch("app.classification.pinecone_store.get_client", return_value=None):
            assert resync_embeddings() == 0

    def test_no_collection_info_returns_zero(self):
        mock_client = MagicMock()
        with patch("app.classification.pinecone_store.get_client", return_value=mock_client), \
             patch("app.classification.pinecone_store.ensure_collection"), \
             patch("app.classification.pinecone_store.get_collection_info", return_value=None):
            assert resync_embeddings() == 0

    def test_no_embeddings_returns_zero(self):
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch("app.classification.pinecone_store.get_client", return_value=mock_client), \
             patch("app.classification.pinecone_store.ensure_collection"), \
             patch("app.classification.pinecone_store.get_collection_info", return_value={"status": "ready"}), \
             patch("app.database.Session", return_value=mock_session):

            assert resync_embeddings() == 0


class TestBytesToEmbedLocal:

    def test_roundtrip(self):
        vec = np.array([0.1, -0.2, 0.3], dtype=np.float32)
        data = struct.pack("3f", *vec)
        result = bytes_to_embed_local(data)
        np.testing.assert_allclose(result, vec, atol=1e-6)

    def test_empty(self):
        assert len(bytes_to_embed_local(b"")) == 0
