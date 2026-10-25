from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from app.database import Base


class PaperSummaryResult(Base):
    __tablename__ = "paper_summary_results"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, unique=True)
    overall_status = Column(String, nullable=False)
    marks_valid = Column(Boolean, nullable=False)
    supported_count = Column(Integer, nullable=False)
    review_count = Column(Integer, nullable=False)
    unrelated_count = Column(Integer, nullable=False)
    aligned_count = Column(Integer, nullable=False)
    mismatch_count = Column(Integer, nullable=False)
    uncertain_count = Column(Integer, nullable=False)
    likely_duplicate_count = Column(Integer, nullable=False)
    possible_duplicate_count = Column(Integer, nullable=False)
    reasons_json = Column(Text, nullable=False)