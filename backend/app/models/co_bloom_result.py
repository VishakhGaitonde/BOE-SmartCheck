from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from app.database import Base


class CoBloomResult(Base):
    __tablename__ = "co_bloom_results"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    bloom_level = Column(String, nullable=False)
    co_code = Column(String, nullable=True)
    co_alignment = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    llm_call_failed = Column(Boolean, default=False)