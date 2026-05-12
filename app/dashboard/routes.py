import json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
from app.database import Session
from app.models.paper import Paper, Report

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = Session()
    total = db.query(Paper).count()
    today_start = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time())
    today_count = db.query(Paper).filter(Paper.ingested_at >= today_start).count()
    reports = db.query(Report).order_by(Report.generated_at.desc()).all()
    db.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_papers": total,
        "papers_today": today_count,
        "reports": reports,
        "periods": ["7d", "6m", "1y"],
    })


@router.post("/ingest")
async def trigger_ingestion():
    from app.ingestion.pipeline import run_ingestion
    from app.classification.dedup import deduplicate
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers
    run_ingestion()
    deduplicate()
    embed_all_papers()    # embeds into both SQLite and Qdrant
    classify_all_papers()  # uses Qdrant when available
    return RedirectResponse("/", status_code=303)


@router.post("/reports/generate")
async def trigger_report(period: str = "7d"):
    from app.reports.generator import generate_report
    result = generate_report(period)
    if "error" in result:
        return RedirectResponse(f"/?error={result['error']}", status_code=303)
    report_id = result.get("id", 0)
    return RedirectResponse(f"/reports/{report_id}", status_code=303)


@router.get("/reports", response_class=HTMLResponse)
async def list_reports(request: Request):
    db = Session()
    reports = db.query(Report).order_by(Report.generated_at.desc()).all()
    db.close()
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "reports": reports,
    })


@router.get("/reports/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: int):
    db = Session()
    report = db.query(Report).filter(Report.id == report_id).first()
    db.close()
    if not report:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("report.html", {
        "request": request,
        "report": report,
    })