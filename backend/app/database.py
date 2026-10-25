from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import (
        paper, document, document_chunk, question,
        validation_result, retrieval_result, unit_textbook_map,
        verification_result, co_bloom_result, boe_decision,
        duplication_result, paper_summary,
    )
    Base.metadata.create_all(bind=engine)