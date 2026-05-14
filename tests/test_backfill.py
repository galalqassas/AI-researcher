"""Tests for app.backfill — backfill pipeline orchestration."""

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from app.backfill import run_backfill


class TestRunBackfill:

    def test_no_new_papers(self):
        with patch("app.backfill.run_ingestion", return_value=(0, [])) as mock_ingest, \
             patch("app.backfill.get_last_published_date", return_value=date(2026, 4, 1)), \
             patch("app.backfill.deduplicate") as mock_dedup, \
             patch("app.backfill.embed_all_papers") as mock_embed, \
             patch("app.backfill.classify_all_papers") as mock_classify:
            result = run_backfill(days=30)
        assert result == {"ingested": 0, "per_bucket": {"general_ai": 0, "autonomous_agents": 0, "ai_finance": 0},
                          "deduplicated": 0, "embedded": 0, "classified": 0}
        assert mock_ingest.call_count == 3
        mock_dedup.assert_not_called()
        mock_embed.assert_not_called()
        mock_classify.assert_not_called()

    def test_backfill_ingests_all_buckets(self):
        bucket_results = {
            "general_ai": (5, [1, 2, 3, 4, 5]),
            "autonomous_agents": (3, [6, 7, 8]),
            "ai_finance": (2, [9, 10]),
        }
        def fake_ingest(*, max_results, bucket, sort_by_date, after_date):
            return bucket_results[bucket]

        with patch("app.backfill.run_ingestion", side_effect=fake_ingest) as mock_ingest, \
             patch("app.backfill.get_last_published_date", return_value=None), \
             patch("app.backfill.deduplicate", return_value=2) as mock_dedup, \
             patch("app.backfill.embed_all_papers", return_value=10) as mock_embed, \
             patch("app.backfill.classify_all_papers", return_value=8) as mock_classify:
            result = run_backfill(days=30, max_results_per_bucket=100)

        assert result["ingested"] == 10
        assert result["per_bucket"] == {"general_ai": 5, "autonomous_agents": 3, "ai_finance": 2}
        assert result["deduplicated"] == 2
        assert result["embedded"] == 10
        assert result["classified"] == 8
        mock_dedup.assert_called_once_with(new_paper_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        mock_embed.assert_called_once_with(paper_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        mock_classify.assert_called_once_with(paper_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        for call in mock_ingest.call_args_list:
            assert call.kwargs["sort_by_date"] is True
            assert call.kwargs["max_results"] == 100

    def test_after_date_computed_from_days(self):
        with patch("app.backfill.run_ingestion", return_value=(0, [])) as mock_ingest, \
             patch("app.backfill.get_last_published_date", return_value=None):
            run_backfill(days=60)
        expected = date.today() - timedelta(days=60)
        for call in mock_ingest.call_args_list:
            assert call.kwargs["after_date"] == expected

    def test_after_date_adjusted_by_last_published_date(self):
        last_pub = date.today() - timedelta(days=5)
        with patch("app.backfill.run_ingestion", return_value=(0, [])) as mock_ingest, \
             patch("app.backfill.get_last_published_date", return_value=last_pub):
            run_backfill(days=30)
        expected = last_pub + timedelta(days=1)
        for call in mock_ingest.call_args_list:
            assert call.kwargs["after_date"] == expected

    def test_after_date_not_adjusted_when_last_pub_is_older(self):
        last_pub = date.today() - timedelta(days=90)
        with patch("app.backfill.run_ingestion", return_value=(0, [])) as mock_ingest, \
             patch("app.backfill.get_last_published_date", return_value=last_pub):
            run_backfill(days=30)
        expected = date.today() - timedelta(days=30)
        for call in mock_ingest.call_args_list:
            assert call.kwargs["after_date"] == expected