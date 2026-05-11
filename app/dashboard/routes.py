from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime
from app.database import Session
from app.models.paper import Paper

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


@router.get("/")
async def dashboard(request: Request):
    db = Session()
    total = db.query(Paper).count()
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    today_count = db.query(Paper).filter(Paper.ingested_at >= today_start).count()
    db.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "total_papers": total, "papers_today": today_count,
    })