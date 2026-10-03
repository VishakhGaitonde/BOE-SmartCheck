import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.paper import Paper
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.question import Question
from app.models.validation_result import ValidationResult

from app.schemas.paper import (
    PaperCreate,
    PaperOut,
    DocumentOut,
    ChunkOut,
    QuestionOut,
    ValidationResultOut,
    SectionResultOut,
    UnitResultOut,
)

from app.utils.file_utils import validate_file, safe_save
from app.processing.extraction import extract_text
from app.processing.cleaning import clean_text
from app.processing.chunking import chunk_document
from app.processing.qp_parser import parse_question_paper
from app.validators.marks_validator import validate_marks, validate_unit_or_pattern
from app.embeddings.embedder import embed_texts
from app.embeddings.vector_store import add_chunks, delete_collection

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("", response_model=PaperOut)
def create_paper(
    payload: PaperCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if payload.pattern not in ("50", "100"):
        raise HTTPException(status_code=400, detail="Pattern must be '50' or '100'")

    if payload.structure_type not in ("SECTION_EQUAL", "UNIT_OR"):
        raise HTTPException(status_code=400, detail="structure_type must be 'SECTION_EQUAL' or 'UNIT_OR'")

    paper = Paper(
        course=payload.course,
        paper_name=payload.paper_name,
        pattern=payload.pattern,
        structure_type=payload.structure_type,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("", response_model=list[PaperOut])
def list_papers(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(Paper).order_by(Paper.uploaded_at.desc()).all()


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post("/{paper_id}/documents", response_model=DocumentOut)
async def upload_document(
    paper_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if document_type not in ("question_paper", "syllabus", "textbook"):
        raise HTTPException(status_code=400, detail="Invalid document_type")

    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    file_bytes = await file.read()
    try:
        validate_file(file.filename, len(file_bytes))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filepath = safe_save(file_bytes, file.filename, paper_id)
    raw_text, was_ocr, pages = extract_text(filepath)
    cleaned = clean_text(raw_text)

    document = Document(
        paper_id=paper_id,
        document_type=document_type,
        filename=file.filename,
        filepath=filepath,
        extracted_text=cleaned,
        pages_json=json.dumps(pages) if pages else None,
        was_ocr="yes" if was_ocr else "no",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/{paper_id}/documents", response_model=list[DocumentOut])
def list_documents(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(Document).filter(Document.paper_id == paper_id).all()


@router.post("/{paper_id}/documents/{document_id}/chunk", response_model=list[ChunkOut])
def chunk_document_endpoint(
    paper_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == document_id, Document.paper_id == paper_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.document_type not in ("syllabus", "textbook"):
        raise HTTPException(status_code=400, detail="Only syllabus/textbook documents can be chunked")

    pages = json.loads(doc.pages_json) if doc.pages_json else None
    chunk_dicts = chunk_document(pages, doc.extracted_text or "")

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

    chunk_objs = []
    for c in chunk_dicts:
        chunk = DocumentChunk(
            paper_id=paper_id,
            document_id=document_id,
            document_type=doc.document_type,
            chunk_index=c["chunk_index"],
            text=c["text"],
            chapter=c["chapter"],
            section=c["section"],
            page=c["page"],
        )
        db.add(chunk)
        chunk_objs.append(chunk)

    db.commit()
    for c in chunk_objs:
        db.refresh(c)
    return chunk_objs


@router.get("/{paper_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    paper_id: int,
    document_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    query = db.query(DocumentChunk).filter(DocumentChunk.paper_id == paper_id)
    if document_type:
        query = query.filter(DocumentChunk.document_type == document_type)
    return query.order_by(DocumentChunk.chunk_index).all()


@router.post("/{paper_id}/documents/{document_id}/parse-questions", response_model=list[QuestionOut])
def parse_questions_endpoint(
    paper_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == document_id, Document.paper_id == paper_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.document_type != "question_paper":
        raise HTTPException(status_code=400, detail="Document must be of type question_paper")

    parsed = parse_question_paper(doc.extracted_text or "")

    db.query(Question).filter(Question.paper_id == paper_id).delete()

    question_objs = []
    for q in parsed:
        question = Question(
            paper_id=paper_id,
            question_number=q["number"],
            question_text=q["text"],
            marks=q["marks"],
            section=q["section"],
            co=q.get("co"),
        )
        db.add(question)
        question_objs.append(question)

    db.commit()

    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper:
        paper.total_questions = len(question_objs)
        paper.calculated_marks = sum(q["marks"] or 0 for q in parsed)
        db.commit()

    for q in question_objs:
        db.refresh(q)
    return question_objs


@router.get("/{paper_id}/questions", response_model=list[QuestionOut])
def list_questions(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(Question).filter(Question.paper_id == paper_id).order_by(Question.id).all()


@router.post("/{paper_id}/validate-marks", response_model=ValidationResultOut)
def validate_marks_endpoint(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    if not questions:
        raise HTTPException(
            status_code=400,
            detail="No parsed questions found. Run parse-questions first.",
        )

    question_dicts = [
        {"question_number": q.question_number, "marks": q.marks, "section": q.section}
        for q in questions
    ]

    try:
        if paper.structure_type == "UNIT_OR":
            result = validate_unit_or_pattern(
                question_dicts, total_marks=int(paper.pattern), num_units=5
            )
            sections_for_storage = []
            unit_results_for_storage = result["unit_results"]
        else:
            result = validate_marks(question_dicts, paper.pattern)
            sections_for_storage = result["sections"]
            unit_results_for_storage = []
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = db.query(ValidationResult).filter(ValidationResult.paper_id == paper_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    expected_total = result.get("expected_total_marks") or result.get("total_expected_marks")
    calculated_total = result.get("calculated_total_marks")
    if calculated_total is None:
        calculated_total = sum(u["actual_marks"] for u in unit_results_for_storage)

    stored_data = sections_for_storage if sections_for_storage else unit_results_for_storage

    validation = ValidationResult(
        paper_id=paper_id,
        pattern=paper.pattern,
        expected_total_marks=expected_total,
        calculated_total_marks=calculated_total,
        overall_valid=result["overall_valid"],
        sections_json=json.dumps(stored_data),
        issues_json=json.dumps(result["issues"]),
    )
    db.add(validation)

    paper.expected_marks = expected_total
    paper.calculated_marks = calculated_total

    db.commit()
    db.refresh(validation)

    return ValidationResultOut(
        id=validation.id,
        paper_id=validation.paper_id,
        pattern=validation.pattern,
        structure_type=paper.structure_type,
        expected_total_marks=validation.expected_total_marks,
        calculated_total_marks=validation.calculated_total_marks,
        overall_valid=validation.overall_valid,
        sections=[SectionResultOut(**s) for s in sections_for_storage],
        unit_results=[UnitResultOut(**u) for u in unit_results_for_storage],
        issues=result["issues"],
    )


@router.get("/{paper_id}/validate-marks", response_model=ValidationResultOut)
def get_marks_validation(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    validation = db.query(ValidationResult).filter(ValidationResult.paper_id == paper_id).first()
    if not validation:
        raise HTTPException(status_code=404, detail="No validation result found. Run validate-marks first.")

    stored_data = json.loads(validation.sections_json)
    is_unit_mode = paper.structure_type == "UNIT_OR"

    return ValidationResultOut(
        id=validation.id,
        paper_id=validation.paper_id,
        pattern=validation.pattern,
        structure_type=paper.structure_type,
        expected_total_marks=validation.expected_total_marks,
        calculated_total_marks=validation.calculated_total_marks,
        overall_valid=validation.overall_valid,
        sections=[] if is_unit_mode else [SectionResultOut(**s) for s in stored_data],
        unit_results=[UnitResultOut(**s) for s in stored_data] if is_unit_mode else [],
        issues=json.loads(validation.issues_json),
    )


@router.post("/{paper_id}/build-knowledge-base")
def build_knowledge_base(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.paper_id == paper_id).all()
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No chunks found. Chunk syllabus and textbook documents first.",
        )

    delete_collection(paper_id)

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    chunk_dicts = [
        {
            "id": f"chunk_{c.id}",
            "text": c.text,
            "document_type": c.document_type,
            "chapter": c.chapter,
            "section": c.section,
            "page": c.page,
        }
        for c in chunks
    ]

    add_chunks(paper_id, chunk_dicts, embeddings)

    return {
        "paper_id": paper_id,
        "chunks_embedded": len(chunks),
        "status": "knowledge base built successfully",
    }