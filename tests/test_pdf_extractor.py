"""Tests for app.ingestion.pdf_extractor — PDF download and text extraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.pdf_extractor import download_pdf, extract_text, extract_paper_text


class TestDownloadPdf:

    def test_success(self, tmp_path):
        with patch("app.ingestion.pdf_extractor.PDFS_DIR", tmp_path), \
             patch("app.ingestion.pdf_extractor.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                raise_for_status=MagicMock(),
                iter_content=MagicMock(return_value=[b"%PDF fake"]),
            )
            result = download_pdf("2401/00001", "https://arxiv.org/pdf/2401.00001")
        assert result is not None and result.exists()

    def test_cached_pdf(self, tmp_path):
        pdf_path = tmp_path / "2401_00001.pdf"
        pdf_path.write_bytes(b"existing")
        with patch("app.ingestion.pdf_extractor.PDFS_DIR", tmp_path):
            assert download_pdf("2401/00001", "https://arxiv.org/pdf/2401.00001") == pdf_path

    def test_download_failure(self, tmp_path):
        with patch("app.ingestion.pdf_extractor.PDFS_DIR", tmp_path), \
             patch("app.ingestion.pdf_extractor.requests.get", side_effect=Exception("fail")):
            assert download_pdf("2401/00001", "https://arxiv.org/1") is None


class TestExtractText:

    def test_text_too_short(self, tmp_path):
        mock_doc = MagicMock()
        mock_page = MagicMock(get_text=MagicMock(return_value="Short"))
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_doc.close = MagicMock()
        with patch("fitz.open", return_value=mock_doc):
            assert extract_text(tmp_path / "t.pdf") is None

    def test_extraction_failure(self, tmp_path):
        with patch("fitz.open", side_effect=Exception("Corrupt")):
            assert extract_text(tmp_path / "t.pdf") is None

    def test_success_with_enough_text(self, tmp_path):
        mock_doc = MagicMock()
        mock_page = MagicMock(get_text=MagicMock(return_value="A" * 200))
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_doc.close = MagicMock()
        with patch("fitz.open", return_value=mock_doc):
            assert extract_text(tmp_path / "t.pdf") == "A" * 200


class TestExtractPaperText:

    def test_download_failure_returns_none(self):
        with patch("app.ingestion.pdf_extractor.download_pdf", return_value=None):
            assert extract_paper_text("1", "https://x") is None