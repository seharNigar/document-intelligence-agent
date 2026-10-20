from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


database_path = Path(__file__).resolve().parent.parent / "document_intelligence.db"
database_url = f"sqlite:///{database_path.as_posix()}"

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def initialize_database():
    from app import conversation_models  # noqa: F401

    Base.metadata.create_all(bind=engine)