"""Tests for app.ingestion.arxiv_client — keyword matching, query building, and fetching."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import ARXIV_KEYWORDS, ARXIV_FROM_DATE
from app.ingestion.arxiv_client import matches_keywords, build_query, fetch_papers, ARXIV_FROM_DATETIME


class TestMatchesKeywords:

    def test_keyword_present(self):
        assert matches_keywords("Recent advances in large language models", "general_ai") is True

    def test_case_insensitive(self):
        assert matches_keywords("AUTONOMOUS AGENTS and multi-agent systems", "autonomous_agents") is True

    def test_keyword_absent(self):
        assert matches_keywords("Quantum computing error correction", "ai_finance") is False

    def test_empty_text(self):
        assert matches_keywords("", "general_ai") is False

    def test_invalid_bucket_raises(self):
        try:
            matches_keywords("some text", "nonexistent_bucket")
            assert False, "Expected KeyError"
        except KeyError:
            pass


class TestBuildQuery:

    def test_basic_query(self):
        query = build_query("general_ai")
        assert "cat:cs.AI" in query
        assert "AND" in query
        for kw in ARXIV_KEYWORDS["general_ai"]:
            assert f'"{kw}"' in query

    def test_query_with_extra(self):
        query = build_query("general_ai", extra_query="cat:cs.CL")
        assert "cat:cs.CL" in query
        assert query.count("AND") >= 2

    def test_query_no_extra(self):
        query = build_query("ai_finance")
        assert "cat:q-fin.ST" in query
        assert "AND" in query


class TestFetchPapers:

    def _make_author(self, name):
        """Create a mock author with a string name."""
        author = MagicMock()
        author.name = name
        return author

    def _make_result(self, arxiv_id, title, summary, published, authors=None, pdf_url=""):
        """Helper to create a mock arxiv.Result."""
        result = MagicMock()
        result.entry_id = f"http://arxiv.org/abs/{arxiv_id}"
        result.title = title
        result.summary = summary
        result.published = published
        if authors is None:
            result.authors = [self._make_author("Test Author")]
        else:
            result.authors = authors

        pdf_link = MagicMock()
        pdf_link.title = "pdf"
        pdf_link.href = pdf_url or f"https://arxiv.org/pdf/{arxiv_id}"
        result.links = [pdf_link]
        return result

    def test_fetch_with_bucket(self):
        """fetch_papers returns structured dicts with correct fields."""
        mock_result = self._make_result(
            "2401.00001",
            "Attention Is All You Need",
            "We propose a new simple network architecture",
            datetime(2024, 1, 15, tzinfo=timezone.utc),
            authors=[self._make_author("A Vaswani"), self._make_author("N Shazeer")],
            pdf_url="https://arxiv.org/pdf/2401.00001",
        )

        mock_client = MagicMock()
        mock_client.results.return_value = [mock_result]

        with patch("app.ingestion.arxiv_client.client", mock_client):
            papers = fetch_papers(bucket="general_ai", max_results=1)

        assert len(papers) == 1
        p = papers[0]
        assert p["arxiv_id"] == "2401.00001"
        assert p["title"] == "Attention Is All You Need"
        assert "Vaswani" in p["authors"]
        assert p["abstract"] == "We propose a new simple network architecture"
        assert p["published_date"] == "2024-01-15"
        assert p["pdf_url"] == "https://arxiv.org/pdf/2401.00001"
        assert "general_ai" in p["buckets"]

    def test_respects_max_results_per_bucket(self):
        """Only max_results papers are returned per bucket."""
        results = [
            self._make_result(f"2401.{i:05d}", f"Paper {i}", "Abstract", datetime(2024, 1, 15, tzinfo=timezone.utc))
            for i in range(5)
        ]
        mock_client = MagicMock()
        mock_client.results.return_value = results

        with patch("app.ingestion.arxiv_client.client", mock_client):
            papers = fetch_papers(bucket="general_ai", max_results=2)

        assert len(papers) == 2

    def test_with_extra_query(self):
        """Extra query is incorporated into the search."""
        mock_client = MagicMock()
        mock_client.results.return_value = []

        with patch("app.ingestion.arxiv_client.client", mock_client):
            fetch_papers(bucket="general_ai", max_results=1, query="cat:cs.CL")

        # Verify the search object was created with the extra query
        search_call = mock_client.results.call_args[0][0]
        assert "cat:cs.CL" in search_call.query

    def test_skips_seen_ids_across_buckets(self):
        """Duplicate arxiv_ids across buckets are deduplicated."""
        shared_result = self._make_result(
            "2401.00001", "Shared Paper", "Abstract", datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        mock_client = MagicMock()
        mock_client.results.return_value = [shared_result]

        with patch("app.ingestion.arxiv_client.client", mock_client):
            papers = fetch_papers(max_results=1)  # searches all buckets

        # Should appear only once even if matched by multiple buckets
        ids = [p["arxiv_id"] for p in papers]
        assert ids.count("2401.00001") == 1

    def test_date_filtering(self):
        """Papers published before ARXIV_FROM_DATE are filtered out."""
        old_result = self._make_result(
            "2001.00001", "Old Paper", "Abstract", datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
        new_result = self._make_result(
            "2401.00001", "New Paper", "Abstract", datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        mock_client = MagicMock()
        mock_client.results.return_value = [old_result, new_result]

        with patch("app.ingestion.arxiv_client.client", mock_client):
            papers = fetch_papers(bucket="general_ai", max_results=2)

        assert len(papers) == 1
        assert papers[0]["arxiv_id"] == "2401.00001"

    def test_error_handling(self):
        """Exceptions during client.results are caught and logged."""
        mock_client = MagicMock()
        mock_client.results.side_effect = Exception("Network error")

        with patch("app.ingestion.arxiv_client.client", mock_client), \
             patch("app.ingestion.arxiv_client.time.sleep"):  # don't actually sleep
            papers = fetch_papers(bucket="general_ai", max_results=1)

        assert papers == []

    def test_pdf_fallback(self):
        """If no pdf link is found, constructs PDF URL from arxiv_id."""
        result = self._make_result(
            "2401.00001", "T", "A", datetime(2024, 1, 15, tzinfo=timezone.utc), pdf_url=""
        )
        # Remove pdf link
        result.links = []

        mock_client = MagicMock()
        mock_client.results.return_value = [result]

        with patch("app.ingestion.arxiv_client.client", mock_client):
            papers = fetch_papers(bucket="general_ai", max_results=1)

        assert papers[0]["pdf_url"] == "https://arxiv.org/pdf/2401.00001"

    def test_multi_bucket_matching(self):
        """If keywords match multiple buckets, all are included."""
        # Use keywords that exist in multiple buckets if possible, or patch matches_keywords
        result = self._make_result(
            "2401.00001", "LLM finance trading", "Abstract", datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        mock_client = MagicMock()
        mock_client.results.return_value = [result]

        def mock_matches(text, bucket):
            return True  # matches all buckets

        with patch("app.ingestion.arxiv_client.client", mock_client), \
             patch("app.ingestion.arxiv_client.matches_keywords", side_effect=mock_matches):
            papers = fetch_papers(bucket="general_ai", max_results=1)

        assert len(papers[0]["buckets"]) == len(ARXIV_KEYWORDS)
