import logging
import requests
from pathlib import Path
from app.config import PDFS_DIR

log = logging.getLogger(__name__)


def download_pdf(arxiv_id: str, pdf_url: str) -> Path | None:
    """Download a PDF from arXiv. Returns local path or None on failure."""
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = PDFS_DIR / f"{arxiv_id.replace('/', '_')}.pdf"

    if pdf_path.exists():
        log.info(f"PDF already exists: {pdf_path}")
        return pdf_path

    try:
        log.info(f"Downloading PDF: {pdf_url}")
        resp = requests.get(pdf_url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(pdf_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return pdf_path
    except Exception as e:
        log.error(f"Failed to download {arxiv_id}: {e}")
        if pdf_path.exists():
            pdf_path.unlink()
        return None


def extract_text(pdf_path: Path) -> str | None:
    """Extract full text from a PDF using pymupdf. Returns text or None."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        if len(text.strip()) < 100:
            log.warning(f"Extracted text too short for {pdf_path.name} ({len(text)} chars)")
            return None
        return text
    except Exception as e:
        log.error(f"Failed to extract text from {pdf_path.name}: {e}")
        return None


def extract_paper_text(arxiv_id: str, pdf_url: str) -> str | None:
    """Download PDF and extract its full text. Returns text or None."""
    pdf_path = download_pdf(arxiv_id, pdf_url)
    if not pdf_path:
        return None
    return extract_text(pdf_path)