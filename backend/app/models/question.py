from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float
from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    question_number = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    marks = Column(Float, nullable=True)
    section = Column(String, nullable=True)
    co = Column(String, nullable=True)