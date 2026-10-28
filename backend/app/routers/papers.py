import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.processing.co_extractor import extract_course_outcomes
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.paper import Paper
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.question import Question
from app.models.validation_result import ValidationResult
from app.agents.combined_agent import verify_and_analyze_batch

from app.agents.combined_agent import verify_and_analyze
from app.schemas.paper import CombinedAnalysisResponse

from app.models.retrieval_result import RetrievalResult
from app.schemas.paper import RetrievalResultOut, EvidenceItemOut
from app.retrieval.retriever import retrieve_evidence
from app.retrieval.unit_mapper import build_unit_textbook_map

from fastapi.responses import FileResponse

from app.models.duplication_result import DuplicationResult
from app.models.paper_summary import PaperSummaryResult
from app.models.boe_decision import BoeDecision
from app.schemas.paper import DuplicationResultOut, PaperSummaryOut
from app.agents.duplication_agent import detect_duplicates
from app.agents.coordinator import aggregate_paper_summary
from app.reports.pdf_report import generate_report

from app.models.co_bloom_result import CoBloomResult
from app.schemas.paper import CoBloomResultOut, AnalyzeCoBloomResponse
from app.agents.co_bloom_agent import analyze_co_bloom

from app.models.boe_decision import BoeDecision
from app.schemas.paper import BoeDecisionIn, BoeDecisionOut, PaperDecisionSummary, VALID_DECISIONS

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

import time

from app.models.verification_result import VerificationResult
from app.schemas.paper import VerificationResultOut
from app.llm.gemini_client import GeminiRateLimitError
from app.schemas.paper import VerifyQuestionsResponse
from app.agents.syllabus_textbook_agent import verify_question

from app.utils.file_utils import validate_file, safe_save
from app.processing.extraction import extract_text
from app.processing.cleaning import clean_text, clean_syllabus_text
from app.processing.chunking import chunk_document
from app.processing.qp_parser import parse_question_paper
from app.validators.marks_validator import validate_marks, validate_unit_or_pattern
from app.embeddings.embedder import embed_texts
from app.embeddings.vector_store import add_chunks, delete_collection

from app.models.unit_textbook_map import UnitTextbookMap
from app.schemas.paper import UnitMapEntryOut

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
    text_for_chunking = doc.extracted_text or ""
    if doc.document_type == "syllabus":
        text_for_chunking = clean_syllabus_text(text_for_chunking)
        if pages:
            pages = [clean_syllabus_text(p) for p in pages]

    chunk_dicts = chunk_document(pages, text_for_chunking)

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
        # calculated_marks intentionally NOT set here — naive summing
        # double-counts UNIT_OR papers (both OR alternatives). validate-marks
        # computes it correctly and now runs automatically right after this
        # step in the one-shot pipeline.
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

def _format_evidence(matches: list[dict]) -> list[dict]:
    formatted = []
    for m in matches:
        meta = m["metadata"]
        formatted.append({
            "text": m["text"],
            "chapter": meta.get("chapter") or None,
            "section": meta.get("section") or None,
            "page": meta.get("page") if meta.get("page", -1) != -1 else None,
            "distance": m["distance"],
            "rerank_score": m.get("rerank_score"),
        })
    return formatted


@router.post("/{paper_id}/retrieve-evidence", response_model=list[RetrievalResultOut])
def retrieve_evidence_endpoint(
    paper_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found. Run parse-questions first.")

    # Clear any previous retrieval results for this paper (idempotent re-run)
    db.query(RetrievalResult).filter(RetrievalResult.paper_id == paper_id).delete()

    results = []
    for q in questions:
        evidence = retrieve_evidence(paper_id, q.question_text, top_k=top_k)

        syllabus_formatted = _format_evidence(evidence["syllabus_evidence"])
        textbook_formatted = _format_evidence(evidence["textbook_evidence"])

        retrieval = RetrievalResult(
            question_id=q.id,
            paper_id=paper_id,
            syllabus_evidence_json=json.dumps(syllabus_formatted),
            textbook_evidence_json=json.dumps(textbook_formatted),
            syllabus_match_found=evidence["syllabus_match_found"],
            matched_unit=evidence["matched_unit"],
            used_narrowed_search=evidence["used_narrowed_search"],
        )
        db.add(retrieval)

        results.append(RetrievalResultOut(
            question_id=q.id,
            syllabus_evidence=[EvidenceItemOut(**e) for e in syllabus_formatted],
            textbook_evidence=[EvidenceItemOut(**e) for e in textbook_formatted],
            syllabus_match_found=evidence["syllabus_match_found"],
            matched_unit=evidence["matched_unit"],
            used_narrowed_search=evidence["used_narrowed_search"],
        ))

    db.commit()
    return results


@router.get("/{paper_id}/questions/{question_id}/evidence", response_model=RetrievalResultOut)
def get_question_evidence(
    paper_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    retrieval = db.query(RetrievalResult).filter(
        RetrievalResult.paper_id == paper_id,
        RetrievalResult.question_id == question_id,
    ).first()
    if not retrieval:
        raise HTTPException(
            status_code=404,
            detail="No retrieval result found for this question. Run retrieve-evidence first.",
        )

    syllabus = json.loads(retrieval.syllabus_evidence_json)
    textbook = json.loads(retrieval.textbook_evidence_json)

    return RetrievalResultOut(
        question_id=question_id,
        syllabus_evidence=[EvidenceItemOut(**e) for e in syllabus],
        textbook_evidence=[EvidenceItemOut(**e) for e in textbook],
        syllabus_match_found=retrieval.syllabus_match_found,
        matched_unit=retrieval.matched_unit,
        used_narrowed_search=retrieval.used_narrowed_search,
    )

@router.post("/{paper_id}/build-unit-textbook-map", response_model=list[UnitMapEntryOut])
def build_unit_textbook_map_endpoint(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    syllabus_chunks = db.query(DocumentChunk).filter(
        DocumentChunk.paper_id == paper_id,
        DocumentChunk.document_type == "syllabus",
    ).all()
    if not syllabus_chunks:
        raise HTTPException(status_code=400, detail="No syllabus chunks found. Chunk and build knowledge base first.")

    chunks_by_unit: dict[str, list[str]] = {}
    for c in syllabus_chunks:
        unit_label = c.chapter or "UNASSIGNED"
        chunks_by_unit.setdefault(unit_label, []).append(c.text)

    chunks_by_unit.pop("UNASSIGNED", None)

    if not chunks_by_unit:
        raise HTTPException(
            status_code=400,
            detail="No unit/chapter headings were detected in the syllabus. Cannot build unit map.",
        )

    syllabus_text_by_unit = {
        unit: "\n".join(texts) for unit, texts in chunks_by_unit.items()
    }

    unit_results = build_unit_textbook_map(paper_id, syllabus_text_by_unit)

    db.query(UnitTextbookMap).filter(UnitTextbookMap.paper_id == paper_id).delete()
    for unit_label, matches in unit_results.items():
        for m in matches:
            db.add(UnitTextbookMap(
                paper_id=paper_id,
                unit_label=unit_label,
                chunk_id=m["chunk_id"],
                distance=m["distance"],
                page=m["page"],
            ))
    db.commit()

    return [
        UnitMapEntryOut(unit_label=unit, chunks_mapped=len(matches))
        for unit, matches in unit_results.items()
    ]


PROACTIVE_DELAY_SECONDS = 12.0  # matches free-tier ~5 RPM spacing


@router.post("/{paper_id}/verify-questions", response_model=VerifyQuestionsResponse)
def verify_questions_endpoint(
    paper_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Runs LLM verification for each question. By default, SKIPS questions that
    already have a stored VerificationResult — so a retry after hitting a
    quota limit only spends calls on questions that haven't succeeded yet.
    Pass force=true to wipe and re-verify everything from scratch.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found. Run parse-questions first.")

    retrievals = {
        r.question_id: r
        for r in db.query(RetrievalResult).filter(RetrievalResult.paper_id == paper_id).all()
    }
    if not retrievals:
        raise HTTPException(status_code=400, detail="No retrieval results found. Run retrieve-evidence first.")

    all_existing = db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).all()
    existing_results = {v.question_id: v for v in all_existing if not v.llm_call_failed}
    if force:
        db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).delete()
        db.commit()
        existing_results = {}
    failed_placeholder_ids = {v.question_id for v in all_existing if v.llm_call_failed}

    # Clean up old failure placeholders so they get freshly re-verified, not
    # treated as duplicates when we insert a new result for the same question.
    if failed_placeholder_ids:
        db.query(VerificationResult).filter(
            VerificationResult.paper_id == paper_id,
            VerificationResult.question_id.in_(failed_placeholder_ids),
        ).delete(synchronize_session=False)
        db.commit()

    if force:
        db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).delete()
        db.commit()
        existing_results = {}

    skipped_count = 0
    newly_verified_count = 0
    stopped_due_to_quota = False
    quota_message = ""

    to_process = []
    for q in questions:
        if q.id in existing_results:
            skipped_count += 1
        else:
            to_process.append(q)

    for idx, q in enumerate(to_process):
        retrieval = retrievals.get(q.id)
        syllabus_evidence = json.loads(retrieval.syllabus_evidence_json) if retrieval else []
        textbook_evidence = json.loads(retrieval.textbook_evidence_json) if retrieval else []

        try:
            verdict = verify_question(q.question_text, syllabus_evidence, textbook_evidence)
        except GeminiRateLimitError as e:
            stopped_due_to_quota = True
            retry_info = f" Retry after ~{int(e.retry_after_seconds)}s." if e.retry_after_seconds else ""
            quota_message = (
                f"Daily LLM quota exhausted after verifying {newly_verified_count} new question(s) "
                f"this run.{retry_info} Run verify-questions again later (without force) to continue "
                f"from where it left off."
            )
            break

        vr = VerificationResult(
            question_id=q.id,
            paper_id=paper_id,
            syllabus_match=verdict["syllabus_match"],
            syllabus_topic=verdict["syllabus_topic"],
            textbook_match=verdict["textbook_match"],
            textbook_reference=verdict["textbook_reference"],
            ai_status=verdict["status"],
            explanation=verdict["explanation"],
            llm_call_failed=verdict.get("llm_call_failed", False),
        )
        db.add(vr)
        try:
            db.commit()
            newly_verified_count += 1
        except IntegrityError:
            db.rollback()

        if idx < len(to_process) - 1:
            time.sleep(PROACTIVE_DELAY_SECONDS)

    all_results = db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).all()

    status_counts = {"SUPPORTED": 0, "POTENTIALLY_UNRELATED": 0, "REQUIRES_REVIEW": 0}
    for r in all_results:
        status_counts[r.ai_status] = status_counts.get(r.ai_status, 0) + 1

    if len(all_results) < len(questions):
        paper.overall_ai_status = "VERIFICATION_INCOMPLETE"
    elif status_counts["POTENTIALLY_UNRELATED"] > 0 or status_counts["REQUIRES_REVIEW"] > 0:
        paper.overall_ai_status = "REQUIRES_BOE_REVIEW"
    else:
        paper.overall_ai_status = "SUPPORTED"
    db.commit()

    if not quota_message:
        quota_message = f"Verified {newly_verified_count} question(s); {skipped_count} already had results."

    return VerifyQuestionsResponse(
        results=[VerificationResultOut.model_validate(r) for r in all_results],
        total_questions=len(questions),
        already_verified_skipped=skipped_count,
        newly_verified=newly_verified_count,
        stopped_due_to_quota=stopped_due_to_quota,
        message=quota_message,
    )


@router.get("/{paper_id}/verifications", response_model=list[VerificationResultOut])
def list_verifications(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).all()


@router.get("/{paper_id}/questions/{question_id}/verification", response_model=VerificationResultOut)
def get_question_verification(
    paper_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    vr = db.query(VerificationResult).filter(
        VerificationResult.paper_id == paper_id,
        VerificationResult.question_id == question_id,
    ).first()
    if not vr:
        raise HTTPException(status_code=404, detail="No verification result found. Run verify-questions first.")

    return VerificationResultOut(
        question_id=vr.question_id,
        syllabus_match=vr.syllabus_match,
        syllabus_topic=vr.syllabus_topic,
        textbook_match=vr.textbook_match,
        textbook_reference=vr.textbook_reference,
        ai_status=vr.ai_status,
        explanation=vr.explanation,
    )

@router.post("/{paper_id}/analyze-co-bloom", response_model=AnalyzeCoBloomResponse)
def analyze_co_bloom_endpoint(
    paper_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found. Run parse-questions first.")

    # CO text comes from the syllabus's "Course Outcomes" section if present —
    # best-effort: we don't have this parsed separately yet, so pass None for
    # now (Gemini falls back to UNCERTAIN alignment per the prompt's own rule).

    syllabus_doc = db.query(Document).filter(
        Document.paper_id == paper_id, Document.document_type == "syllabus"
    ).first()
    co_text_by_code = extract_course_outcomes(syllabus_doc.extracted_text or "") if syllabus_doc else {}

    all_existing = db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).all()
    existing_results = {v.question_id: v for v in all_existing if not v.llm_call_failed}
    failed_ids = {v.question_id for v in all_existing if v.llm_call_failed}

    if failed_ids:
        db.query(CoBloomResult).filter(
            CoBloomResult.paper_id == paper_id,
            CoBloomResult.question_id.in_(failed_ids),
        ).delete(synchronize_session=False)
        db.commit()

    skipped = sum(1 for q in questions if q.id in existing_results)
    to_process = [q for q in questions if q.id not in existing_results]

    newly_analyzed = 0
    stopped_due_to_quota = False
    quota_message = ""

    for idx, q in enumerate(to_process):
        co_text = co_text_by_code.get(q.co)

        try:
            result = analyze_co_bloom(q.question_text, q.co, co_text)
        except GeminiRateLimitError as e:
            stopped_due_to_quota = True
            quota_message = f"Daily LLM quota exhausted after {newly_analyzed} new question(s). Run again later to continue."
            break

        cb = CoBloomResult(
            question_id=q.id,
            paper_id=paper_id,
            bloom_level=result["bloom_level"],
            co_code=result["co_code"],
            co_alignment=result["co_alignment"],
            explanation=result["explanation"],
            llm_call_failed=result.get("llm_call_failed", False),
        )
        db.add(cb)
        try:
            db.commit()
            newly_analyzed += 1
        except IntegrityError:
            # Another concurrent run already inserted a result for this
            # question (e.g. a double-click or two open tabs triggering
            # the endpoint close together) — safe to skip, not a real error.
            db.rollback()

        if idx < len(to_process) - 1:
            time.sleep(PROACTIVE_DELAY_SECONDS)

    all_results = db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).all()

    if not quota_message:
        quota_message = f"Analyzed {newly_analyzed} question(s); {skipped} already had results."

    return AnalyzeCoBloomResponse(
        results=[CoBloomResultOut.model_validate(r) for r in all_results],
        total_questions=len(questions),
        already_analyzed_skipped=skipped,
        newly_analyzed=newly_analyzed,
        stopped_due_to_quota=stopped_due_to_quota,
        message=quota_message,
    )


@router.get("/{paper_id}/co-bloom-results", response_model=list[CoBloomResultOut])
def list_co_bloom_results(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).all()

BATCH_SIZE = 5  # questions per Gemini call — cuts total API calls ~5x


@router.post("/{paper_id}/verify-and-analyze", response_model=CombinedAnalysisResponse)
def verify_and_analyze_endpoint(
    paper_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found.")

    retrievals = {r.question_id: r for r in db.query(RetrievalResult).filter(RetrievalResult.paper_id == paper_id).all()}
    if not retrievals:
        raise HTTPException(status_code=400, detail="No retrieval results found.")

    from app.processing.co_extractor import extract_course_outcomes
    syllabus_doc = db.query(Document).filter(Document.paper_id == paper_id, Document.document_type == "syllabus").first()
    co_text_by_code = extract_course_outcomes(syllabus_doc.extracted_text or "") if syllabus_doc else {}

    if force:
        db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).delete()
        db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).delete()
        db.commit()

    done_vr = {v.question_id for v in db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id, VerificationResult.llm_call_failed == False).all()}
    done_cb = {c.question_id for c in db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id, CoBloomResult.llm_call_failed == False).all()}
    already_done = done_vr & done_cb

    to_process = [q for q in questions if q.id not in already_done]
    skipped = len(questions) - len(to_process)
    newly_processed = 0
    stopped_due_to_quota = False
    quota_message = ""

    batches = [to_process[i:i + BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        items = []
        for i, q in enumerate(batch):
            retrieval = retrievals.get(q.id)
            syllabus_evidence = json.loads(retrieval.syllabus_evidence_json) if retrieval else []
            textbook_evidence = json.loads(retrieval.textbook_evidence_json) if retrieval else []
            items.append({
                "index": i,
                "question_id": q.id,
                "question_text": q.question_text,
                "co_code": q.co,
                "co_text": co_text_by_code.get(q.co),
                "syllabus_evidence": syllabus_evidence,
                "textbook_evidence": textbook_evidence,
            })

        try:
            batch_results = verify_and_analyze_batch(items)
        except GeminiRateLimitError as e:
            stopped_due_to_quota = True
            quota_message = f"Daily LLM quota exhausted after {newly_processed} question(s). Resume later."
            break

        for item, result in zip(items, batch_results):
            q_id = item["question_id"]

            db.query(VerificationResult).filter(VerificationResult.question_id == q_id).delete()
            db.query(CoBloomResult).filter(CoBloomResult.question_id == q_id).delete()

            db.add(VerificationResult(
                question_id=q_id, paper_id=paper_id,
                syllabus_match=result["syllabus_match"], syllabus_topic=result["syllabus_topic"],
                textbook_match=result["textbook_match"], textbook_reference=result["textbook_reference"],
                ai_status=result["status"], explanation=result["explanation"],
                llm_call_failed=result["llm_call_failed"],
            ))
            db.add(CoBloomResult(
                question_id=q_id, paper_id=paper_id,
                bloom_level=result["bloom_level"], co_code=item["co_code"],
                co_alignment=result["co_alignment"], explanation=result["co_bloom_explanation"],
                llm_call_failed=result["llm_call_failed"],
            ))
            try:
                db.commit()
                newly_processed += 1
            except IntegrityError:
                db.rollback()

        if batch_idx < len(batches) - 1:
            time.sleep(PROACTIVE_DELAY_SECONDS)

    if not quota_message:
        quota_message = f"Processed {newly_processed} question(s); {skipped} already had results."

    return CombinedAnalysisResponse(
        total_questions=len(questions), already_done_skipped=skipped,
        newly_processed=newly_processed, stopped_due_to_quota=stopped_due_to_quota,
        message=quota_message,
    )

@router.put("/{paper_id}/questions/{question_id}/decision", response_model=BoeDecisionOut)
def save_boe_decision(
    paper_id: int,
    question_id: int,
    payload: BoeDecisionIn,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if payload.decision not in VALID_DECISIONS:
        raise HTTPException(status_code=400, detail=f"decision must be one of {VALID_DECISIONS}")

    question = db.query(Question).filter(Question.id == question_id, Question.paper_id == paper_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    verification = db.query(VerificationResult).filter(VerificationResult.question_id == question_id).first()
    ai_status = verification.ai_status if verification else None

    existing = db.query(BoeDecision).filter(BoeDecision.question_id == question_id).first()

    if existing:
        existing.decision = payload.decision
        existing.comment = payload.comment
        existing.ai_status_at_decision = ai_status
        existing.decided_by = current_user
        db.commit()
        db.refresh(existing)
        decision_obj = existing
    else:
        decision_obj = BoeDecision(
            question_id=question_id,
            paper_id=paper_id,
            ai_status_at_decision=ai_status,
            decision=payload.decision,
            comment=payload.comment,
            decided_by=current_user,
        )
        db.add(decision_obj)
        db.commit()
        db.refresh(decision_obj)

    # Update paper-level final_boe_status: PENDING if any question still
    # undecided, else a summary reflecting whether everything was accepted
    # or something was rejected/overridden.
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    all_questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    all_decisions = db.query(BoeDecision).filter(BoeDecision.paper_id == paper_id).all()
    decision_map = {d.question_id: d.decision for d in all_decisions}

    if len(all_decisions) < len(all_questions) or any(d == "PENDING" for d in decision_map.values()):
        paper.final_boe_status = "PENDING"
    elif any(d == "REJECT" for d in decision_map.values()):
        paper.final_boe_status = "REJECTED"
    elif any(d == "OVERRIDE" for d in decision_map.values()):
        paper.final_boe_status = "OVERRIDDEN"
    else:
        paper.final_boe_status = "ACCEPTED"
    db.commit()

    return decision_obj


@router.get("/{paper_id}/questions/{question_id}/decision", response_model=BoeDecisionOut)
def get_boe_decision(
    paper_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    decision = db.query(BoeDecision).filter(
        BoeDecision.paper_id == paper_id, BoeDecision.question_id == question_id
    ).first()
    if not decision:
        raise HTTPException(status_code=404, detail="No decision recorded yet for this question.")
    return decision


@router.get("/{paper_id}/decisions", response_model=list[BoeDecisionOut])
def list_boe_decisions(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(BoeDecision).filter(BoeDecision.paper_id == paper_id).all()


@router.get("/{paper_id}/decisions/summary", response_model=PaperDecisionSummary)
def get_decision_summary(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    total = db.query(Question).filter(Question.paper_id == paper_id).count()
    decisions = db.query(BoeDecision).filter(BoeDecision.paper_id == paper_id).all()

    decided = len(decisions)
    accepted = sum(1 for d in decisions if d.decision == "ACCEPT")
    rejected = sum(1 for d in decisions if d.decision == "REJECT")
    overridden = sum(1 for d in decisions if d.decision == "OVERRIDE")

    return PaperDecisionSummary(
        total_questions=total,
        decided=decided,
        pending=total - decided,
        accepted=accepted,
        rejected=rejected,
        overridden=overridden,
    )


@router.post("/{paper_id}/detect-duplicates", response_model=list[DuplicationResultOut])
def detect_duplicates_endpoint(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    questions = db.query(Question).filter(Question.paper_id == paper_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found. Run parse-questions first.")

    pairs = detect_duplicates([{"id": q.id, "text": q.question_text} for q in questions])

    db.query(DuplicationResult).filter(DuplicationResult.paper_id == paper_id).delete()
    for p in pairs:
        db.add(DuplicationResult(
            paper_id=paper_id,
            question_id_a=p["question_id_a"],
            question_id_b=p["question_id_b"],
            similarity=p["similarity"],
            status=p["status"],
            explanation=p["explanation"],
        ))
    db.commit()

    return db.query(DuplicationResult).filter(DuplicationResult.paper_id == paper_id).all()


@router.get("/{paper_id}/duplicates", response_model=list[DuplicationResultOut])
def list_duplicates(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return db.query(DuplicationResult).filter(DuplicationResult.paper_id == paper_id).all()


@router.post("/{paper_id}/aggregate-summary", response_model=PaperSummaryOut)
def aggregate_summary_endpoint(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    validation = db.query(ValidationResult).filter(ValidationResult.paper_id == paper_id).first()
    marks_valid = validation.overall_valid if validation else False

    verification_results = db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).all()
    co_bloom_results = db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).all()
    duplication_results = db.query(DuplicationResult).filter(DuplicationResult.paper_id == paper_id).all()

    summary = aggregate_paper_summary(marks_valid, verification_results, co_bloom_results, duplication_results)

    existing = db.query(PaperSummaryResult).filter(PaperSummaryResult.paper_id == paper_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    db.add(PaperSummaryResult(
        paper_id=paper_id,
        overall_status=summary["overall_status"],
        marks_valid=summary["marks_valid"],
        supported_count=summary["supported_count"],
        review_count=summary["review_count"],
        unrelated_count=summary["unrelated_count"],
        aligned_count=summary["aligned_count"],
        mismatch_count=summary["mismatch_count"],
        uncertain_count=summary["uncertain_count"],
        likely_duplicate_count=summary["likely_duplicate_count"],
        possible_duplicate_count=summary["possible_duplicate_count"],
        reasons_json=json.dumps(summary["reasons"]),
    ))

    paper.overall_ai_status = summary["overall_status"]
    db.commit()

    return PaperSummaryOut(**summary)


@router.get("/{paper_id}/summary", response_model=PaperSummaryOut)
def get_paper_summary(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    row = db.query(PaperSummaryResult).filter(PaperSummaryResult.paper_id == paper_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No summary generated yet. Run aggregate-summary first.")

    return PaperSummaryOut(
        overall_status=row.overall_status, marks_valid=row.marks_valid,
        supported_count=row.supported_count, review_count=row.review_count,
        unrelated_count=row.unrelated_count, aligned_count=row.aligned_count,
        mismatch_count=row.mismatch_count, uncertain_count=row.uncertain_count,
        likely_duplicate_count=row.likely_duplicate_count,
        possible_duplicate_count=row.possible_duplicate_count,
        reasons=json.loads(row.reasons_json),
    )


@router.get("/{paper_id}/report")
def download_report(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    questions = db.query(Question).filter(Question.paper_id == paper_id).order_by(Question.id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found.")

    verifications_by_qid = {v.question_id: v for v in db.query(VerificationResult).filter(VerificationResult.paper_id == paper_id).all()}
    co_bloom_by_qid = {c.question_id: c for c in db.query(CoBloomResult).filter(CoBloomResult.paper_id == paper_id).all()}
    decisions_by_qid = {d.question_id: d for d in db.query(BoeDecision).filter(BoeDecision.paper_id == paper_id).all()}
    validation = db.query(ValidationResult).filter(ValidationResult.paper_id == paper_id).first()
    duplication_pairs = db.query(DuplicationResult).filter(DuplicationResult.paper_id == paper_id).all()

    marks_valid = validation.overall_valid if validation else False
    summary = aggregate_paper_summary(
        marks_valid,
        list(verifications_by_qid.values()),
        list(co_bloom_by_qid.values()),
        duplication_pairs,
    )

    filepath = generate_report(paper, questions, verifications_by_qid, co_bloom_by_qid, decisions_by_qid, validation, summary, duplication_pairs)

    return FileResponse(filepath, media_type="application/pdf", filename=f"{paper.paper_name}_report.pdf")