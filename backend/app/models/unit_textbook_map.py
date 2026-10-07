from sqlalchemy import Column, Integer, String, ForeignKey, Float
from app.database import Base


class UnitTextbookMap(Base):
    __tablename__ = "unit_textbook_map"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    unit_label = Column(String, nullable=False)
    chunk_id = Column(String, nullable=False)
    distance = Column(Float, nullable=False)
    page = Column(Integer, nullable=True)