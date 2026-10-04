import re

CHAPTER_PATTERN = re.compile(r'^\s*(Chapter|Unit)\s+(\d+|[IVXLC]+)\b[:\-]?\s*(.*)', re.IGNORECASE)
SECTION_NUM_PATTERN = re.compile(r'^\s*(\d+\.\d+)\s+(.*)')

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def chunk_document(pages: list[str] | None, full_text: str) -> list[dict]:
    """
    Splits document text into overlapping chunks, tagging each chunk with
    the heading that was actually in effect AT THAT POINT in the text —
    not the last heading found anywhere on the page.
    """
    chunks = []
    current_chapter = None
    current_section = None
    chunk_index = 0

    if pages:
        for page_num, page_text in enumerate(pages, start=1):
            pieces, current_chapter, current_section = _split_with_headings(
                page_text, current_chapter, current_section
            )
            for piece_text, chapter, section in pieces:
                chunks.append({
                    "text": piece_text,
                    "chapter": chapter,
                    "section": section,
                    "page": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
    else:
        pieces, current_chapter, current_section = _split_with_headings(
            full_text, current_chapter, current_section
        )
        for piece_text, chapter, section in pieces:
            chunks.append({
                "text": piece_text,
                "chapter": chapter,
                "section": section,
                "page": None,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    return chunks


def _split_with_headings(text: str, current_chapter, current_section):
    """
    Walks the text line by line, updating heading state as it goes, and
    buffers lines into chunks. Each chunk is tagged with whatever heading
    was active at the moment its lines were being buffered — not a
    heading that appears later in the same page.
    """
    lines = text.split("\n")
    pieces = []
    buffer_lines = []
    buffer_chapter = current_chapter
    buffer_section = current_section

    def buffer_len():
        return sum(len(l) + 1 for l in buffer_lines)

    for line in lines:
        ch_match = CHAPTER_PATTERN.match(line)
        if ch_match:
            current_chapter = line.strip()
        sec_match = SECTION_NUM_PATTERN.match(line)
        if sec_match:
            current_section = sec_match.group(1)

        buffer_lines.append(line)

        if buffer_len() >= CHUNK_SIZE:
            piece_text = "\n".join(buffer_lines).strip()
            if piece_text:
                pieces.append((piece_text, buffer_chapter, buffer_section))

            # Keep overlap: retain the tail of the buffer for context continuity
            overlap_text = piece_text[-CHUNK_OVERLAP:] if len(piece_text) > CHUNK_OVERLAP else piece_text
            buffer_lines = [overlap_text]
            buffer_chapter = current_chapter
            buffer_section = current_section

    # Flush remaining buffer
    piece_text = "\n".join(buffer_lines).strip()
    if piece_text:
        pieces.append((piece_text, buffer_chapter, buffer_section))

    return pieces, current_chapter, current_section