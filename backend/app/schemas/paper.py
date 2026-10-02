from pydantic import BaseModel
from datetime import datetime


class PaperCreate(BaseModel):
    course: str | None = None
    paper_name: str
    pattern: str  # "50" or "100"


class PaperOut(BaseModel):
    id: int
    course: str | None
    paper_name: str
    exam_type: str
    pattern: str
    uploaded_at: datetime
    final_boe_status: str

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    paper_id: int
    document_type: str
    filename: str
    was_ocr: str

    class Config:
        from_attributes = True

class ChunkOut(BaseModel):
    id: int
    document_id: int
    document_type: str
    chunk_index: int
    text: str
    chapter: str | None
    section: str | None
    page: int | None

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: int
    question_number: str
    question_text: str
    marks: float | None
    section: str | None

    class Config:
        from_attributes = True