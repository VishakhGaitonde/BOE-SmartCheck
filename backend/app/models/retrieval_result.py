from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean
from app.database import Base


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    syllabus_evidence_json = Column(Text, nullable=False)
    textbook_evidence_json = Column(Text, nullable=False)
    syllabus_match_found = Column(Boolean, default=False)