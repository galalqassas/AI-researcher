import time
import logging
from datetime import date, datetime
import arxiv
from tqdm import tqdm
from app.config import (
    ARXIV_CATEGORIES, ARXIV_KEYWORDS, BUCKETS,
    ARXIV_FROM_DATE, ARXIV_MAX_RESULTS,
)

log = logging.getLogger(__name__)

client = arxiv.Client(
    page_size=50,
    delay_seconds=10.0,
    num_retries=5,
)

ARXIV_FROM_DATETIME = datetime.strptime(ARXIV_FROM_DATE, "%Y-%m-%d")


def matches_keywords(text: str, bucket: str) -> bool:
    """Check if text contains any keyword for the given bucket (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in ARXIV_KEYWORDS[bucket])


def build_query(bucket: str, extra_query: str = None, after_date: date = None, before_date: date = None) -> str:
    """Build an arXiv API query string for a bucket using categories + keywords.
    after_date: If set, only return papers submitted on or after this date.
    before_date: If set, only return papers submitted before this date."""
    cats = ARXIV_CATEGORIES[bucket]
    cat_part = " OR ".join(f"cat:{c}" for c in cats)
    kws = ARXIV_KEYWORDS[bucket]
    kw_part = " OR ".join(f'"{kw}"' for kw in kws)
    parts = [f"({cat_part})", f"({kw_part})"]
    if extra_query:
        parts.append(f"({extra_query})")
    if after_date is not None and before_date is not None:
        after_str = after_date.strftime("%Y%m%d") + "0000"
        before_str = before_date.strftime("%Y%m%d") + "2359"
        parts.append(f"submittedDate:[{after_str} TO {before_str}]")
    elif after_date is not None:
        date_str = after_date.strftime("%Y%m%d") + "0000"
        parts.append(f"submittedDate:[{date_str} TO 209912310000]")
    elif before_date is not None:
        before_str = before_date.strftime("%Y%m%d") + "2359"
        parts.append(f"submittedDate:[200001010000 TO {before_str}]")
    return " AND ".join(parts)


def fetch_papers(bucket: str = None, max_results: int = None, query: str = None,
                 sort_by_date: bool = False, after_date: date = None, before_date: date = None,
                 silent: bool = False):
    """Fetch papers from arXiv. If bucket is given, use category+keyword filtering.
    If query is given, use it directly. Returns list of dicts with paper metadata.
    sort_by_date: Sort by SubmittedDate (newest first) instead of Relevance.
    after_date: If set, only fetch papers submitted on or after this date (server-side filter).
    before_date: If set, only fetch papers submitted before this date (server-side filter)."""
    max_results = max_results or ARXIV_MAX_RESULTS
    buckets_to_search = [bucket] if bucket else BUCKETS
    fetch_limit = max_results if (after_date or before_date) else max_results * 3
    all_papers = []
    seen_ids = set()

    bucket_iter = buckets_to_search if silent else tqdm(buckets_to_search, desc="Buckets")
    for b in bucket_iter:
        search_query = build_query(b, extra_query=query, after_date=after_date, before_date=before_date)

        # Client-side before_date filter
        before_dt = datetime(before_date.year, before_date.month, before_date.day) if before_date else None
        log.info(f"Searching arXiv for bucket '{b}': {search_query}")

        sort_criterion = arxiv.SortCriterion.SubmittedDate if sort_by_date else arxiv.SortCriterion.Relevance
        search = arxiv.Search(
            query=search_query,
            max_results=fetch_limit,
            sort_by=sort_criterion,
        )

        bucket_count = 0
        try:
            results_iter = client.results(search)
            if not silent:
                results_iter = tqdm(results_iter, desc=f"  Papers ({b})", leave=False)
            for result in results_iter:
                arxiv_id = result.entry_id.split("/abs/")[-1]
                if arxiv_id in seen_ids:
                    continue

                pub_dt = result.published.replace(tzinfo=None) if result.published else None
                if pub_dt and pub_dt < ARXIV_FROM_DATETIME:
                    continue
                if pub_dt and before_dt and pub_dt >= before_dt:
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