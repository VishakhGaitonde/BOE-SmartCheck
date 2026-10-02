import re

CHAPTER_PATTERN = re.compile(r'^\s*(Chapter|Unit)\s+(\d+|[IVXLC]+)\b[:\-]?\s*(.*)', re.IGNORECASE)
SECTION_NUM_PATTERN = re.compile(r'^\s*(\d+\.\d+)\s+(.*)')

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def chunk_document(pages: list[str] | None, full_text: str) -> list[dict]:
    """
    Splits document text into overlapping chunks, tagging each with the
    most recently seen chapter/section heading and page number (if known).
    """
    chunks = []
    current_chapter = None
    current_section = None
    chunk_index = 0

    if pages:
        for page_num, page_text in enumerate(pages, start=1):
            current_chapter, current_section = _update_headings(
                page_text, current_chapter, current_section
            )
            for piece in _split_text(page_text):
                chunks.append({
                    "text": piece,
                    "chapter": current_chapter,
                    "section": current_section,
                    "page": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
    else:
        current_chapter, current_section = _update_headings(
            full_text, current_chapter, current_section
        )
        for piece in _split_text(full_text):
            chunks.append({
                "text": piece,
                "chapter": current_chapter,
                "section": current_section,
                "page": None,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    return chunks


def _update_headings(text: str, current_chapter, current_section):
    for line in text.split("\n"):
        ch_match = CHAPTER_PATTERN.match(line)
        if ch_match:
            current_chapter = line.strip()
        sec_match = SECTION_NUM_PATTERN.match(line)
        if sec_match:
            current_section = sec_match.group(1)
    return current_chapter, current_section


def _split_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    pieces = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        start = end - CHUNK_OVERLAP
    return pieces