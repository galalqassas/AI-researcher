import json
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from app.database import Session
from app.models.paper import Paper, Report, PipelineRun

router = APIRouter()


@router.post("/ingest")
async def trigger_ingestion():
    """Run the full ingestion pipeline: ingest → dedup → embed → classify."""
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

    return JSONResponse({
        "status": "ok",
        "paper_count": added,
        "stages": {
            "ingested": added,
            "deduplicated": removed,
            "embedded": embedded,
            "classified": classified,
        },
    })


@router.post("/reports/generate")
async def trigger_report(period: str = "7d"):
    """Generate a report for the given period."""
    from app.metrics import track_pipeline
    from app.reports.generator import generate_report

    try:
        with track_pipeline("report") as ctx:
            result = generate_report(period)
            if "error" in result:
                return JSONResponse({"error": result["error"]}, status_code=500)
            ctx["paper_count"] = result.get("papers", 0)
            ctx["stages_json"] = result
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)

    return JSONResponse({
        "id": result.get("id", 0) if result else 0,
        "period": period,
        "paper_count": result.get("papers", 0) if result else 0,
    })


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


@router.get("/reports", response_class=JSONResponse)
async def list_reports():
    """List all reports as JSON."""
    db = Session()
    reports = db.query(Report).order_by(Report.generated_at.desc()).all()
    db.close()
    return JSONResponse([{
        "id": r.id,
        "period": r.period,
        "generated_at": str(r.generated_at),
        "paper_count": r.paper_count,
        "content_html": r.content_html,
    } for r in reports])


@router.get("/reports/{report_id}", response_class=JSONResponse)
async def view_report(report_id: int):
    """Get a single report as JSON."""
    db = Session()
    report = db.query(Report).filter(Report.id == report_id).first()
    db.close()
    if not report:
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return JSONResponse({
        "id": report.id,
        "period": report.period,
        "generated_at": str(report.generated_at),
        "paper_count": report.paper_count,
        "content_html": report.content_html,
    })