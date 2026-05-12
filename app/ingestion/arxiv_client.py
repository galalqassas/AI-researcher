import time
import logging
import arxiv
from datetime import datetime
from tqdm import tqdm
from app.config import (
    ARXIV_CATEGORIES, ARXIV_KEYWORDS, BUCKETS,
    ARXIV_FROM_DATE, ARXIV_MAX_RESULTS,
)
log = logging.getLogger(__name__)

client = arxiv.Client(
    page_size=100,
    delay_seconds=3.0,
    num_retries=3,
)


def build_query(bucket: str, extra_query: str = None) -> str:
    """Build an arXiv API query string for a bucket using categories + keywords + date filter."""
    cats = ARXIV_CATEGORIES[bucket]
    cat_part = " OR ".join(f"cat:{c}" for c in cats)
    kws = ARXIV_KEYWORDS[bucket]
    kw_part = " OR ".join(f'"{kw}"' for kw in kws)
    date_part = f"submittedDate:[{ARXIV_FROM_DATE.replace('-', '')} TO 99999999]"
    parts = [f"({cat_part})", f"({kw_part})", date_part]
    if extra_query:
        parts.append(f"({extra_query})")
    return " AND ".join(parts)


def fetch_papers(bucket: str = None, max_results: int = None, query: str = None):
    """Fetch papers from arXiv. If bucket is given, use category+keyword filtering.
    If query is given, use it directly. Returns list of dicts with paper metadata."""
    max_results = max_results or ARXIV_MAX_RESULTS
    buckets_to_search = [bucket] if bucket else BUCKETS
    all_papers = []
    seen_ids = set()

    for b in tqdm(buckets_to_search, desc="Buckets"):
        search_query = build_query(b, query) if query else build_query(b)
        log.info(f"Searching arXiv for bucket '{b}': {search_query}")

        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        try:
            for result in tqdm(client.results(search), desc=f"  Papers ({b})", leave=False):
                arxiv_id = result.entry_id.split("/abs/")[-1]
                if arxiv_id in seen_ids:
                    continue

                title = result.title.replace("\n", " ").strip()
                abstract = result.summary.replace("\n", " ").strip()

                matched_buckets = [b]

                pdf_url = ""
                for link in result.links:
                    if link.title == "pdf":
                        pdf_url = link.href
                        break
                if not pdf_url:
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

                paper = {
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "authors": ", ".join(a.name for a in result.authors),
                    "abstract": abstract,
                    "pdf_url": pdf_url,
                    "published_date": result.published.strftime("%Y-%m-%d") if result.published else None,
                    "buckets": matched_buckets,
                }

                seen_ids.add(arxiv_id)
                all_papers.append(paper)

        except Exception as e:
            log.error(f"Error fetching bucket '{b}': {e}")
            time.sleep(3)
            continue

    log.info(f"Fetched {len(all_papers)} unique papers total")
    return all_papers