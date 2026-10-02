from pathlib import Path
import fitz
import docx

from app.processing.ocr import ocr_pdf_pages

MIN_TEXT_CHARS_PER_PAGE = 20


def extract_text(filepath: str) -> tuple[str, bool, list[str] | None]:
    """
    Returns (full_text, was_ocr_used, pages_list_or_None)
    pages_list is only populated for PDFs (page-aware); None for DOCX.
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(filepath)
    elif ext == ".docx":
        return _extract_docx(filepath), False, None
    else:
        raise ValueError(f"Unsupported file type for extraction: {ext}")


def _extract_pdf(filepath: str) -> tuple[str, bool, list[str]]:
    doc = fitz.open(filepath)
    pages = []
    needs_ocr = False

    for page in doc:
        page_text = page.get_text().strip()
        if len(page_text) < MIN_TEXT_CHARS_PER_PAGE:
            needs_ocr = True
        pages.append(page_text)

    doc.close()
    combined = "\n".join(pages).strip()

    if needs_ocr and len(combined) < MIN_TEXT_CHARS_PER_PAGE * 2:
        ocr_pages = ocr_pdf_pages(filepath)
        return "\n".join(ocr_pages).strip(), True, ocr_pages

    return combined, False, pages


def _extract_docx(filepath: str) -> str:
    doc = docx.Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)