from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func

from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    course = Column(String, nullable=True)
    paper_name = Column(String, nullable=False)
    exam_type = Column(String, default="SEE")
    pattern = Column(String, nullable=False)  # "50" or "100"
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    total_questions = Column(Integer, nullable=True)
    expected_marks = Column(Float, nullable=True)
    calculated_marks = Column(Float, nullable=True)
    overall_ai_status = Column(String, nullable=True)
    final_boe_status = Column(String, default="PENDING")