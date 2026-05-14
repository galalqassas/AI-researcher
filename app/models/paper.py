from datetime import date, datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, Date, DateTime, LargeBinary, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arxiv_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    buckets: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    def __repr__(self):
        return f"<Paper {self.arxiv_id}>"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    paper_count: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self):
        return f"<Report {self.period} - {self.paper_count} papers>"


class PipelineRun(Base):
    """Track pipeline execution history: timing, status, errors."""
    __tablename__ = "pipeline_runs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="ingest|report|full_pipeline")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Duration in seconds")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="success|error|running")
    stages_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON stage details")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paper_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self):
        return f"<PipelineRun {self.name} {self.status}>"