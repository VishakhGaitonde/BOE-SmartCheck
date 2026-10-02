from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    document_type = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    pages_json = Column(Text, nullable=True)  # JSON list of per-page text, PDFs only
    was_ocr = Column(String, default="no")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())