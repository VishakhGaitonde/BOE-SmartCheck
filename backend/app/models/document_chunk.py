from sqlalchemy import Column, Integer, String, ForeignKey, Text
from app.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    document_type = Column(String, nullable=False)  # syllabus | textbook
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    chapter = Column(String, nullable=True)
    section = Column(String, nullable=True)
    page = Column(Integer, nullable=True)