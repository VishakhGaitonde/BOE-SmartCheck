from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float
from app.database import Base


class DuplicationResult(Base):
    __tablename__ = "duplication_results"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    question_id_a = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_id_b = Column(Integer, ForeignKey("questions.id"), nullable=False)
    similarity = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)