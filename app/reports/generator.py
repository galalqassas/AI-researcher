import json
import logging
from datetime import datetime, timedelta
from tqdm import tqdm
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from app.config import OLLAMA_MODEL, REPORT_PERIODS
from app.database import Session
from app.models.paper import Paper, Report
from app.reports.prompts import BUCKET_SUMMARY, CROSS_BUCKET_SYNTHESIS, PER_PAPER_SUMMARY

log = logging.getLogger(__name__)

PERIOD_DAYS = {
    "7d": 7,
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
}

llm = OllamaLLM(model=OLLAMA_MODEL)


def get_papers_for_period(period: str, session):
    """Query papers published within the given period."""
    days = PERIOD_DAYS.get(period, 30)
    cutoff = datetime.utcnow() - timedelta(days=days)
    return session.query(Paper).filter(Paper.ingested_at >= cutoff).all()


def summarize_paper(paper) -> str:
    """Generate a 1-2 sentence summary of a single paper."""
    prompt = PromptTemplate.from_template(PER_PAPER_SUMMARY)
    chain = prompt | llm
    try:
        return chain.invoke({"title": paper.title, "abstract": paper.abstract or ""}).strip()
    except Exception as e:
        log.error(f"Failed to summarize {paper.arxiv_id}: {e}")
        return f"{paper.title} — (summary unavailable)"


def format_papers_for_bucket(papers, bucket: str) -> str:
    """Format papers in a bucket as a readable list for the LLM."""
    lines = []
    for p in papers:
        lines.append(f"- {p.title} ({p.published_date}): {p.abstract[:300]}")
    return "\n".join(lines[:20])


def summarize_bucket(bucket: str, papers) -> str:
    """Generate a plain-English summary for all papers in a bucket."""
    if not papers:
        return f"No papers found in the '{bucket}' category for this period."

    paper_text = format_papers_for_bucket(papers, bucket)
    prompt = PromptTemplate.from_template(BUCKET_SUMMARY)
    chain = prompt | llm
    try:
        return chain.invoke({"bucket": bucket, "papers": paper_text}).strip()
    except Exception as e:
        log.error(f"Failed to summarize bucket {bucket}: {e}")
        return f"Summary generation failed for {bucket}."


def generate_cross_synthesis(summaries: dict) -> str:
    """Generate cross-bucket synthesis."""
    prompt = PromptTemplate.from_template(CROSS_BUCKET_SYNTHESIS)
    chain = prompt | llm
    try:
        return chain.invoke({
            "general_ai": summaries.get("general_ai", "No papers."),
            "autonomous_agents": summaries.get("autonomous_agents", "No papers."),
            "ai_finance": summaries.get("ai_finance", "No papers."),
        }).strip()
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
            html += f"<li><strong>{p.title}</strong> ({p.published_date}) — <a href=\"{p.pdf_url}\" target=\"_blank\">PDF</a></li>\n"
        html += "</ul>\n<hr>\n"

    html += "<h2>Cross-Domain Insights</h2>\n"
    html += f"<div>{cross_synthesis}</div>\n"
    return html


def generate_report(period: str) -> dict:
    """Generate a research report for the given time period."""
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
        generated_at=datetime.utcnow(),
        content_html=content_html,
        paper_count=len(papers),
    )
    session.add(report)
    session.commit()

    result = {"id": report.id, "period": period, "papers": len(papers)}
    log.info(f"Report generated: {result}")
    session.close()
    return result