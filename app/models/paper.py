from sqlalchemy import Integer, String, Text, Date, DateTime, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arxiv_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text)
    pdf_url: Mapped[str] = mapped_column(Text)
    published_date: Mapped[str] = mapped_column(Date)
    ingested_at: Mapped[str] = mapped_column(DateTime)
    buckets: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)

    def __repr__(self):
        return f"<Paper {self.arxiv_id}>"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    generated_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    paper_count: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self):
        return f"<Report {self.period} - {self.paper_count} papers>"