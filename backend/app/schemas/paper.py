from pydantic import BaseModel
from datetime import datetime


class PaperCreate(BaseModel):
    course: str | None = None
    paper_name: str
    pattern: str  # total marks as string: "50" or "100"
    structure_type: str = "SECTION_EQUAL"  # or "UNIT_OR"


class PaperOut(BaseModel):
    id: int
    course: str | None
    paper_name: str
    exam_type: str
    pattern: str
    structure_type: str
    uploaded_at: datetime
    total_questions: int | None = None
    expected_marks: float | None = None
    calculated_marks: float | None = None
    overall_ai_status: str | None = None
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
    co: str | None

    class Config:
        from_attributes = True

class SectionResultOut(BaseModel):
    section: str
    expected_marks: float
    actual_marks: float
    valid: bool


class UnitResultOut(BaseModel):
    unit: str
    question_number: str
    expected_marks: float
    actual_marks: float
    valid: bool


class ValidationResultOut(BaseModel):
    id: int
    paper_id: int
    pattern: str
    structure_type: str
    expected_total_marks: float
    calculated_total_marks: float
    overall_valid: bool
    sections: list[SectionResultOut] = []
    unit_results: list[UnitResultOut] = []
    issues: list[str]

    class Config:
        from_attributes = True

class EvidenceItemOut(BaseModel):
    text: str
    chapter: str | None = None
    section: str | None = None
    page: int | None = None
    distance: float
    rerank_score: float | None = None


class RetrievalResultOut(BaseModel):
    question_id: int
    syllabus_evidence: list[EvidenceItemOut]
    textbook_evidence: list[EvidenceItemOut]
    syllabus_match_found: bool
    matched_unit: str | None = None
    used_narrowed_search: bool = False


class UnitMapEntryOut(BaseModel):
    unit_label: str
    chunks_mapped: int

class VerificationResultOut(BaseModel):
    question_id: int
    syllabus_match: bool
    syllabus_topic: str | None
    textbook_match: bool
    textbook_reference: str | None
    ai_status: str
    explanation: str

    class Config:
        from_attributes = True

class VerifyQuestionsResponse(BaseModel):
    results: list[VerificationResultOut]
    total_questions: int
    already_verified_skipped: int
    newly_verified: int
    stopped_due_to_quota: bool
    message: str

class CoBloomResultOut(BaseModel):
    question_id: int
    bloom_level: str
    co_code: str | None
    co_alignment: str
    explanation: str

    class Config:
        from_attributes = True


class AnalyzeCoBloomResponse(BaseModel):
    results: list[CoBloomResultOut]
    total_questions: int
    already_analyzed_skipped: int
    newly_analyzed: int
    stopped_due_to_quota: bool
    message: str

class CombinedAnalysisResponse(BaseModel):
    total_questions: int
    already_done_skipped: int
    newly_processed: int
    stopped_due_to_quota: bool
    message: str

VALID_DECISIONS = {"ACCEPT", "REJECT", "OVERRIDE", "PENDING"}


class BoeDecisionIn(BaseModel):
    decision: str  # ACCEPT | REJECT | OVERRIDE | PENDING
    comment: str | None = None


class BoeDecisionOut(BaseModel):
    question_id: int
    ai_status_at_decision: str | None
    decision: str
    comment: str | None
    decided_by: str
    decided_at: datetime

    class Config:
        from_attributes = True


class PaperDecisionSummary(BaseModel):
    total_questions: int
    decided: int
    pending: int
    accepted: int
    rejected: int
    overridden: int