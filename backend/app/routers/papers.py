from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.paper import Paper
from app.models.document import Document
from app.schemas.paper import PaperCreate, PaperOut, DocumentOut, ChunkOut, QuestionOut
from app.utils.file_utils import validate_file, safe_save
from app.processing.extraction import extract_text
from app.processing.cleaning import clean_text

import json

from app.processing.chunking import chunk_document
from app.processing.qp_parser import parse_question_paper
from app.models.document_chunk import DocumentChunk
from app.models.question import Question


router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("", response_model=PaperOut)
def create_paper(
    payload: PaperCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if payload.pattern not in ("50", "100"):
        raise HTTPException(status_code=400, detail="Pattern must be '50' or '100'")

    paper = Paper(
        course=payload.course,
        paper_name=payload.paper_name,
        pattern=payload.pattern,
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
    document_type: str = Form(...),  # question_paper | syllabus | textbook
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

    raw_text, was_ocr = extract_text(filepath)
    cleaned = clean_text(raw_text)

    document = Document(
        paper_id=paper_id,
        document_type=document_type,
        filename=file.filename,
        filepath=filepath,
        extracted_text=cleaned,
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

    # Clear any previous chunks for this document (re-chunk safe)
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
        )
        db.add(question)
        question_objs.append(question)

    db.commit()

    paper.total_questions = len(question_objs) if (paper := db.query(Paper).get(paper_id)) else None
    if paper:
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