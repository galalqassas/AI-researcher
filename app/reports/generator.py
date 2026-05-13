import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tqdm import tqdm
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from app.config import OLLAMA_MODEL, OLLAMA_MODEL_LIGHT, OLLAMA_MAX_TOKENS_PER_RUN, REPORT_PERIODS
from app.database import Session
from app.models.paper import Paper, Report
from app.reports.prompts import BUCKET_SUMMARY, CROSS_BUCKET_SYNTHESIS, PER_PAPER_SUMMARY

log = logging.getLogger(__name__)

PERIOD_DAYS = {
    "7d": 7,
    "6m": 180,
    "1y": 365,
}

# --- Tiered model routing: light for summaries, heavy for synthesis ---
llm_light = OllamaLLM(model=OLLAMA_MODEL_LIGHT)
llm_heavy = OllamaLLM(model=OLLAMA_MODEL)

# --- LLM response cache (persisted to JSON, loaded once per run) ---
_cache_path = Path(__file__).resolve().parent.parent.parent / "data" / "llm_cache.json"
_llm_cache: dict | None = None
_tokens_used = 0


def _ensure_cache() -> dict:
    """Load the LLM cache from disk if not already loaded."""
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache
    if _cache_path.exists():
        try:
            _llm_cache = json.loads(_cache_path.read_text())
        except Exception:
            log.warning("Failed to load LLM cache, starting fresh")
            _llm_cache = {}
    else:
        _llm_cache = {}
    return _llm_cache


def _persist_cache():
    """Write the LLM cache to disk (only called on cache misses)."""
    global _llm_cache
    if _llm_cache is None:
        return
    _cache_path.parent.mkdir(parents=True, exist_ok=True)
    _cache_path.write_text(json.dumps(_llm_cache, ensure_ascii=False))


def _cached_invoke(llm_instance, prompt_text: str) -> str:
    """Call LLM with cache: return cached response if available, else call and store."""
    global _tokens_used
    key = hashlib.sha256(f"{llm_instance.model}:{prompt_text}".encode()).hexdigest()
    cache = _ensure_cache()
    if key in cache:
        log.info("LLM cache hit")
        return cache[key]
    result = llm_instance.invoke(prompt_text).strip()
    _tokens_used += len(prompt_text.split()) + len(result.split())
    if OLLAMA_MAX_TOKENS_PER_RUN > 0 and _tokens_used > OLLAMA_MAX_TOKENS_PER_RUN:
        _persist_cache()
        raise RuntimeError(f"Token cap exceeded: {_tokens_used} > {OLLAMA_MAX_TOKENS_PER_RUN}")
    cache[key] = result
    _persist_cache()
    return result


def get_papers_for_period(period: str, session):
    """Query papers published within the given period."""
    days = PERIOD_DAYS.get(period, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return session.query(Paper).filter(Paper.ingested_at >= cutoff).all()


def summarize_paper(paper) -> str:
    """Generate a 1-2 sentence summary of a single paper."""
    prompt = PromptTemplate.from_template(PER_PAPER_SUMMARY).format(
        title=paper.title, abstract=paper.abstract or ""
    )
    try:
        return _cached_invoke(llm_light, prompt)
    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"Failed to summarize {paper.arxiv_id}: {e}")
        return f"{paper.title} — (summary unavailable)"


def format_papers_for_bucket(papers) -> str:
    """Format papers in a bucket as a readable list for the LLM."""
    lines = []
    for p in papers:
        lines.append(f"- {p.title} ({p.published_date}): {p.abstract[:300]}")
    return "\n".join(lines[:20])


def summarize_bucket(bucket: str, papers) -> str:
    """Generate a plain-English summary for all papers in a bucket."""
    if not papers:
        return f"No papers found in the '{bucket}' category for this period."

    paper_text = format_papers_for_bucket(papers)
    prompt = PromptTemplate.from_template(BUCKET_SUMMARY).format(
        bucket=bucket, papers=paper_text
    )
    try:
        return _cached_invoke(llm_heavy, prompt)
    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"Failed to summarize bucket {bucket}: {e}")
        return f"Summary generation failed for {bucket}."


def generate_cross_synthesis(summaries: dict) -> str:
    """Generate cross-bucket synthesis."""
    prompt = PromptTemplate.from_template(CROSS_BUCKET_SYNTHESIS).format(
        general_ai=summaries.get("general_ai", "No papers."),
        autonomous_agents=summaries.get("autonomous_agents", "No papers."),
        ai_finance=summaries.get("ai_finance", "No papers."),
    )
    try:
        return _cached_invoke(llm_heavy, prompt)
    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"Cross-bucket synthesis failed: {e}")
        return "Cross-domain synthesis unavailable."


def build_html_report(summaries: dict, cross_synthesis: str, papers_by_bucket: dict, period: str) -> str:
    """Build the final HTML content for the report."""
    bucket_labels = {
        "general_ai": "General AI",
        "autonomous_agents": "Autonomous Agents",
        "ai_finance": "AI + Finance",
    }

    html = ""
    for bucket, label in bucket_labels.items():
        papers = papers_by_bucket.get(bucket, [])
        html += f"<h2>{label}</h2>\n"
        html += f"<p><em>{len(papers)} papers in this category</em></p>\n"
        html += f"<h3>Key Themes</h3>\n<div>{summaries.get(bucket, '')}</div>\n"
        html += "<h3>Important Papers</h3><ul>\n"
        for p in papers[:10]:
            date_str = str(p.published_date) if p.published_date else "N/A"
            pdf_link = f'<a href="{p.pdf_url}" target="_blank">PDF</a>' if p.pdf_url else "(no PDF)"
            html += f"<li><strong>{p.title}</strong> ({date_str}) — {pdf_link}</li>\n"
        html += "</ul>\n<hr>\n"

    html += "<h2>Cross-Domain Insights</h2>\n"
    html += f"<div>{cross_synthesis}</div>\n"
    return html


def generate_report(period: str) -> dict:
    """Generate a research report for the given time period."""
    global _llm_cache, _tokens_used
    _llm_cache = None  # force reload from disk
    _tokens_used = 0

    if period not in REPORT_PERIODS:
        raise ValueError(f"Invalid period: {period}. Must be one of {REPORT_PERIODS}")

    log.info(f"Generating report for period: {period}")
    session = Session()

    papers = get_papers_for_period(period, session)
    if not papers:
        session.close()
        return {"error": f"No papers found for period {period}"}

    papers_by_bucket = {}
    for p in papers:
        buckets = json.loads(p.buckets) if p.buckets else ["general_ai"]
        for b in buckets:
            papers_by_bucket.setdefault(b, []).append(p)

    # Per-paper summaries (light model)
    for p in papers:
        if not hasattr(p, '_summary'):
            try:
                p._summary = summarize_paper(p)
            except RuntimeError:
                raise
            except Exception:
                p._summary = None

    summaries = {}
    for bucket in tqdm(["general_ai", "autonomous_agents", "ai_finance"], desc="Summarizing buckets"):
        bp = papers_by_bucket.get(bucket, [])
        log.info(f"Summarizing bucket '{bucket}' ({len(bp)} papers)...")
        summaries[bucket] = summarize_bucket(bucket, bp)

    log.info("Generating cross-domain synthesis...")
    cross_synthesis = generate_cross_synthesis(summaries)

    content_html = build_html_report(summaries, cross_synthesis, papers_by_bucket, period)

    report = Report(
        period=period,
        generated_at=datetime.now(timezone.utc),
        content_html=content_html,
        paper_count=len(papers),
    )
    session.add(report)
    session.commit()

    result = {"id": report.id, "period": period, "papers": len(papers)}
    log.info(f"Report generated: {result}")
    session.close()
    return result