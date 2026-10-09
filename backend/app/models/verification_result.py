from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from app.database import Base


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    syllabus_match = Column(Boolean, default=False)
    syllabus_topic = Column(String, nullable=True)
    textbook_match = Column(Boolean, default=False)
    textbook_reference = Column(String, nullable=True)
    ai_status = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    llm_call_failed = Column(Boolean, default=False)  # True = error placeholder, eligible for retry