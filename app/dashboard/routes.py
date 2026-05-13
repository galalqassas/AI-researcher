import json
import concurrent.futures
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from sqlalchemy import func
from app.database import Session
from app.models.paper import Paper, Report, PipelineRun
from app.config import BUCKETS, REPORT_TIMEOUT

router = APIRouter()


@router.get("/papers")
async def list_papers(
    bucket: str = Query(default=None, description="Filter by bucket key"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=200, description="Results per page"),
):
    """List papers with optional bucket filter and pagination."""
    db = Session()
    query = db.query(Paper)
    if bucket and bucket in BUCKETS:
        query = query.filter(Paper.buckets.contains(f'"{bucket}"'))
    total = query.count()
    papers = query.order_by(Paper.ingested_at.desc()).offset((page - 1) * limit).limit(limit).all()
    db.close()
    return JSONResponse({
        "total": total,
        "page": page,
        "limit": limit,
        "results": [{
            "id": p.id,
            "arxiv_id": p.arxiv_id,
            "title": p.title,
            "authors": p.authors,
            "abstract": p.abstract,
            "published_date": str(p.published_date) if p.published_date else None,
            "ingested_at": str(p.ingested_at) if p.ingested_at else None,
            "buckets": json.loads(p.buckets) if p.buckets else [],
        } for p in papers],
    })


@router.get("/papers/stats")
async def paper_stats():
    """Paper counts: total, per bucket, and per month for charts."""
    db = Session()
    total = db.query(Paper).count()
    # Papers ingested today
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today = db.query(Paper).filter(
        func.strftime("%Y-%m-%d", Paper.ingested_at) == today_str
    ).count()

    per_bucket = {}
    for bucket_key in BUCKETS:
        per_bucket[bucket_key] = db.query(Paper).filter(
            Paper.buckets.contains(f'"{bucket_key}"')
        ).count()
    # Per-month aggregation for charts
    per_date_rows = db.query(
        func.strftime("%Y-%m", Paper.ingested_at).label("month"),
        func.count(Paper.id).label("count"),
    ).filter(Paper.ingested_at.isnot(None)).group_by("month").order_by("month").all()
    # Also get per-month per-bucket counts
    per_date = []
    for month, count in per_date_rows:
        bucket_counts = {}
        for bk in BUCKETS:
            bucket_counts[bk] = db.query(Paper).filter(
                Paper.ingested_at.isnot(None),
                func.strftime("%Y-%m", Paper.ingested_at) == month,
                Paper.buckets.contains(f'"{bk}"'),
            ).count()
        per_date.append({"month": month, "count": count, **bucket_counts})
    db.close()
    return JSONResponse({
        "total": total,
        "today": today,
        "per_bucket": per_bucket,
        "per_date": per_date,
    })


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
    """Generate a report for the given period. Fails if generation exceeds REPORT_TIMEOUT."""
    from app.metrics import track_pipeline
    from app.reports.generator import generate_report

    try:
        with track_pipeline("report") as ctx:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(generate_report, period)
                try:
                    result = future.result(timeout=REPORT_TIMEOUT if REPORT_TIMEOUT > 0 else None)
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(
                        f"Report generation exceeded {REPORT_TIMEOUT}s timeout"
                    )
            if "error" in result:
                return JSONResponse({"error": result["error"]}, status_code=422)
            ctx["paper_count"] = result.get("papers", 0)
            ctx["stages_json"] = result
    except TimeoutError as exc:
        return JSONResponse({"error": str(exc)}, status_code=504)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)

    return JSONResponse({
        "id": result.get("id", 0) if result else 0,
        "period": period,
        "paper_count": result.get("papers", 0) if result else 0,
    })


@router.get("/search", response_class=JSONResponse)
async def search_papers(q: str = Query(..., min_length=1), limit: int = Query(default=10, ge=1, le=50)):
    """Hybrid search: embeds the query, searches Pinecone + FTS5, merges via RRF."""
    from app.classification.embedder import get_embedding
    from app.classification.pinecone_store import search_similar
    from app.classification.classifier import _bm25_search, RRF_K

    # Dense search via Pinecone
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