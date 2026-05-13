from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_session():
    """Context manager that yields a session and guarantees close on exit.

    Usage:
        with get_session() as session:
            session.add(obj)
            session.commit()
    """
    session = Session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(engine)
    # Create FTS5 virtual table for BM25 keyword search
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract)"
        ))
        conn.commit()


def rebuild_fts():
    """Rebuild FTS index from all papers in SQLite."""
    from app.models.paper import Paper
    with get_session() as session:
        papers = session.query(Paper).all()
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM papers_fts"))
            for p in papers:
                conn.execute(
                    text("INSERT INTO papers_fts (rowid, title, abstract) VALUES (:id, :title, :abstract)"),
                    {"id": p.id, "title": p.title or "", "abstract": p.abstract or ""},
                )
            conn.commit()