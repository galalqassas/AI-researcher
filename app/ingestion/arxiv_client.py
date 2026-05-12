import time
import logging
from datetime import datetime
import arxiv
from tqdm import tqdm
from app.config import (
    ARXIV_CATEGORIES, ARXIV_KEYWORDS, BUCKETS,
    ARXIV_FROM_DATE, ARXIV_MAX_RESULTS,
)

log = logging.getLogger(__name__)

client = arxiv.Client(
    page_size=50,
    delay_seconds=5.0,
    num_retries=5,
)

ARXIV_FROM_DATETIME = datetime.strptime(ARXIV_FROM_DATE, "%Y-%m-%d")


def matches_keywords(text: str, bucket: str) -> bool:
    """Check if text contains any keyword for the given bucket (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in ARXIV_KEYWORDS[bucket])


def build_query(bucket: str, extra_query: str = None) -> str:
    """Build an arXiv API query string for a bucket using categories + keywords.

    NOTE: The arXiv API returns HTTP 500 when combining submittedDate
    filter/sort with multi-category queries. We sort by Relevance and
    filter dates client-side instead.
    """
    cats = ARXIV_CATEGORIES[bucket]
    cat_part = " OR ".join(f"cat:{c}" for c in cats)
    kws = ARXIV_KEYWORDS[bucket]
    kw_part = " OR ".join(f'"{kw}"' for kw in kws)
    parts = [f"({cat_part})", f"({kw_part})"]
    if extra_query:
        parts.append(f"({extra_query})")
    return " AND ".join(parts)


def fetch_papers(bucket: str = None, max_results: int = None, query: str = None):
    """Fetch papers from arXiv. If bucket is given, use category+keyword filtering.
    If query is given, use it directly. Returns list of dicts with paper metadata.
    Date filtering is done client-side to avoid arXiv API HTTP 500 errors."""
    max_results = max_results or ARXIV_MAX_RESULTS
    buckets_to_search = [bucket] if bucket else BUCKETS
    # Fetch extra to compensate for client-side date filtering
    fetch_limit = max_results * 3
    all_papers = []
    seen_ids = set()

    for b in tqdm(buckets_to_search, desc="Buckets"):
        search_query = build_query(b, query) if query else build_query(b)
        log.info(f"Searching arXiv for bucket '{b}': {search_query}")

        search = arxiv.Search(
            query=search_query,
            max_results=fetch_limit,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        bucket_count = 0
        try:
            for result in tqdm(client.results(search), desc=f"  Papers ({b})", leave=False):
                arxiv_id = result.entry_id.split("/abs/")[-1]
                if arxiv_id in seen_ids:
                    continue

                # Client-side date filter
                if result.published and result.published.replace(tzinfo=None) < ARXIV_FROM_DATETIME:
                    continue

                title = result.title.replace("\n", " ").strip()
                abstract = result.summary.replace("\n", " ").strip()
                text = f"{title} {abstract}"

                matched_buckets = [b]
                if matches_keywords(text, b):
                    for other_b in BUCKETS:
                        if other_b != b and matches_keywords(text, other_b):
                            matched_buckets.append(other_b)

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
                bucket_count += 1
                if bucket_count >= max_results:
                    break

        except Exception as e:
            log.error(f"Error fetching bucket '{b}': {e}")
            time.sleep(5)
            continue

    log.info(f"Fetched {len(all_papers)} unique papers total")
    return all_papers