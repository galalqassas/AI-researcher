"""Tests for app.ingestion.arxiv_client — keyword matching and query building."""

from app.config import ARXIV_KEYWORDS
from app.ingestion.arxiv_client import matches_keywords, build_query


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