from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Float
from app.database import Base


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, unique=True)
    pattern = Column(String, nullable=False)
    expected_total_marks = Column(Float, nullable=False)
    calculated_total_marks = Column(Float, nullable=False)
    overall_valid = Column(Boolean, nullable=False)
    sections_json = Column(Text, nullable=False)   # JSON list of per-section results
    issues_json = Column(Text, nullable=False)      # JSON list of issue strings