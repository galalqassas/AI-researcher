from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    Base.metadata.create_all(engine)