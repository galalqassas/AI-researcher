import json
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
from app.database import Session
from app.models.paper import Paper, Report, PipelineRun

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = Session()
    total = db.query(Paper).count()
    today_start = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time())
    today_count = db.query(Paper).filter(Paper.ingested_at >= today_start).count()
    reports = db.query(Report).order_by(Report.generated_at.desc()).all()
    last_run = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    db.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_papers": total,
        "papers_today": today_count,
        "reports": reports,
        "periods": ["7d", "6m", "1y"],
        "last_run": last_run,
    })


@router.post("/ingest")
async def trigger_ingestion():
    from app.metrics import track_pipeline
    from app.ingestion.pipeline import run_ingestion
    from app.classification.dedup import deduplicate
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers

    with track_pipeline("ingest") as ctx:
        added = run_ingestion()
        removed = deduplicate()
        embedded = embed_all_papers()
        classified = classify_all_papers()
        ctx["paper_count"] = added
        ctx["stages_json"] = {
            "ingested": added,
            "deduplicated": removed,
            "embedded": embedded,
            "classified": classified,
        }

    return RedirectResponse("/", status_code=303)


@router.post("/reports/generate")
async def trigger_report(period: str = "7d"):
    from app.metrics import track_pipeline
    from app.reports.generator import generate_report

    result = None
    try:
        with track_pipeline("report") as ctx:
            result = generate_report(period)
            if "error" in result:
                raise RuntimeError(result["error"])
            ctx["paper_count"] = result.get("papers", 0)
            ctx["stages_json"] = result
    except Exception:
        if result and "error" in result:
            return RedirectResponse(f"/?error={result['error']}", status_code=303)
        raise

    report_id = result.get("id", 0) if result else 0
    return RedirectResponse(f"/reports/{report_id}", status_code=303)


@router.get("/search", response_class=JSONResponse)
async def search_papers(q: str = Query(..., min_length=1), limit: int = Query(default=10, ge=1, le=50)):
    """Hybrid search: embeds the query, searches Qdrant + FTS5, merges via RRF."""
    from app.classification.embedder import get_embedding
    from app.classification.qdrant_store import search_similar
    from app.classification.classifier import _bm25_search, RRF_K

    # Dense search via Qdrant
    query_vec = get_embedding(q)
    scores: dict[int, float] = {}
    if query_vec is not None:
        hits = search_similar(query_vec, limit=limit)
        for rank, hit in enumerate(hits):
            scores[hit["id"]] = scores.get(hit["id"], 0) + 1.0 / (RRF_K + rank + 1)

    # Sparse search via FTS5
    for rank, (pid, _score) in enumerate(_bm25_search(q, limit=limit)):
        scores[pid] = scores.get(pid, 0) + 1.0 / (RRF_K + rank + 1)

    # Build response ranked by RRF score
    ranked_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]
    db = Session()
    results = []
    for pid in ranked_ids:
        paper = db.get(Paper, pid)
        if paper:
            results.append({
                "id": paper.id,
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": (paper.abstract or "")[:200],
                "published_date": str(paper.published_date) if paper.published_date else None,
                "buckets": json.loads(paper.buckets) if paper.buckets else [],
                "score": round(scores[pid], 4),
            })
    db.close()
    return JSONResponse({"query": q, "results": results})


@router.get("/pipeline-runs", response_class=JSONResponse)
async def list_pipeline_runs(limit: int = Query(default=20, ge=1, le=100)):
    db = Session()
    runs = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit).all()
    db.close()
    return JSONResponse([{
        "id": r.id,
        "name": r.name,
        "started_at": str(r.started_at),
        "finished_at": str(r.finished_at) if r.finished_at else None,
        "duration_s": r.duration_s,
        "status": r.status,
        "paper_count": r.paper_count,
        "error": r.error,
        "stages": json.loads(r.stages_json) if r.stages_json else {},
    } for r in runs])


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