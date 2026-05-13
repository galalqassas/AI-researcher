"""Tests for app.reports.generator — LLM cache, formatting, report generation."""

import struct
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.paper import Paper, Report
from app.reports.generator import (
    REPORT_PERIODS, build_html_report, format_papers_for_bucket,
    generate_report, get_papers_for_period, summarize_paper, _cached_invoke,
)
from app.reports.prompts import BUCKET_SUMMARY, CROSS_BUCKET_SYNTHESIS, PER_PAPER_SUMMARY


class TestFormatPapersForBucket:

    def test_truncation_at_20(self):
        papers = [MagicMock(title=f"P{i}", published_date=date(2024, 1, 1), abstract="x" * 200) for i in range(25)]
        assert len(format_papers_for_bucket(papers).split("\n")) == 20

    def test_empty_list(self):
        assert format_papers_for_bucket([]) == ""

    def test_abstract_truncated_to_300(self):
        result = format_papers_for_bucket([MagicMock(title="T", published_date="d", abstract="x" * 500)])
        assert "x" * 300 in result


class TestBuildHtmlReport:

    def test_generates_sections(self):
        papers = [MagicMock(title="P1", published_date=date(2024, 1, 1), pdf_url="https://x", abstract="a")]
        html = build_html_report({"general_ai": "AI sum"}, "synth", {"general_ai": papers}, "7d")
        assert "AI sum" in html and "Cross-Domain Insights" in html and "1 papers" in html

    def test_empty_bucket_shows_zero(self):
        assert "0 papers" in build_html_report({}, "synth", {}, "7d")


class TestGetPapersForPeriod:

    @pytest.fixture
    def period_engine(self):
        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(eng)
        with eng.connect() as conn:
            conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"))
            conn.commit()
        return eng

    @pytest.fixture
    def period_session(self, period_engine):
        session = sessionmaker(bind=period_engine)()
        yield session
        session.close()

    def test_unknown_period_defaults_to_30(self, period_session):
        assert isinstance(get_papers_for_period("99d", period_session), list)

    def test_known_period(self, period_session):
        assert isinstance(get_papers_for_period("7d", period_session), list)


class TestCachedInvoke:

    def test_token_cap_raises_runtime_error(self, tmp_path):
        mock_llm = MagicMock(model="test-model")
        mock_llm.invoke.return_value = "word " * 200  # 200 words
        cache_file = tmp_path / "cache.json"
        with patch("app.reports.generator._cache_path", cache_file), \
             patch("app.reports.generator._llm_cache", {}), \
             patch("app.reports.generator.OLLAMA_MAX_TOKENS_PER_RUN", 5), \
             patch("app.reports.generator._tokens_used", 0):
            with pytest.raises(RuntimeError):
                _cached_invoke(mock_llm, "prompt" * 50)  # 50 words prompt + 200 words response > 5


class TestSummarizePaper:

    def test_fallback_on_llm_error(self):
        paper = MagicMock(arxiv_id="1", title="T", abstract="A")
        mock_llm = MagicMock(model="test-model")
        mock_llm.invoke.side_effect = Exception("down")
        with patch("app.reports.generator._get_llm_light", return_value=mock_llm), \
             patch("app.reports.generator._llm_cache", {}), \
             patch("app.reports.generator._tokens_used", 0), \
             patch("app.reports.generator.OLLAMA_MAX_TOKENS_PER_RUN", 0):
            assert "summary unavailable" in summarize_paper(paper)


class TestGenerateReport:

    def test_invalid_period_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid period"):
            generate_report("2w")

    def test_no_papers_returns_error(self, db_engine, db_session):
        with patch("app.reports.generator.Session", return_value=db_session):
            result = generate_report("7d")
        assert "error" in result


class TestPromptTemplates:

    @pytest.mark.parametrize("template,placeholders", [
        (BUCKET_SUMMARY, ["{bucket}", "{papers}"]),
        (CROSS_BUCKET_SYNTHESIS, ["{general_ai}", "{autonomous_agents}", "{ai_finance}"]),
        (PER_PAPER_SUMMARY, ["{title}", "{abstract}"]),
    ])
    def test_placeholders_exist(self, template, placeholders):
        for ph in placeholders:
            assert ph in template