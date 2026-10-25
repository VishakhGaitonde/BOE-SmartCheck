from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class BoeDecision(Base):
    __tablename__ = "boe_decisions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    ai_status_at_decision = Column(String, nullable=True)  # snapshot of AI status when decided
    decision = Column(String, nullable=False)  # ACCEPT | REJECT | OVERRIDE | PENDING
    comment = Column(Text, nullable=True)
    decided_by = Column(String, nullable=False)  # username
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())