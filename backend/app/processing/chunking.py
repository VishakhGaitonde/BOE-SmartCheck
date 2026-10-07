import re

CHAPTER_PATTERN = re.compile(r'^\s*(Chapter|Unit)\s+(\S+)\b[:\-]?\s*(.*)', re.IGNORECASE)
SECTION_NUM_PATTERN = re.compile(r'^\s*(\d+\.\d+)\s+(.*)')

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

ROMAN_SEQUENCE = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

def chunk_document(pages: list[str] | None, full_text: str) -> list[dict]:
    """
    Splits document text into overlapping chunks, tagging each chunk with
    the heading in effect at that point. Heading numerals are assigned by
    sequential position (handles unreliable OCR numeral reads). Small
    trailing fragments are merged into the previous chunk AFTER processing
    the whole document, so merging works across page boundaries too.
    """
    raw_pieces = []  # (text, chapter, section, page)
    current_chapter = None
    current_section = None
    heading_counts = {}

    if pages:
        for page_num, page_text in enumerate(pages, start=1):
            pieces, current_chapter, current_section = _split_with_headings(
                page_text, current_chapter, current_section, heading_counts
            )
            for piece_text, chapter, section in pieces:
                raw_pieces.append((piece_text, chapter, section, page_num))
    else:
        pieces, current_chapter, current_section = _split_with_headings(
            full_text, current_chapter, current_section, heading_counts
        )
        for piece_text, chapter, section in pieces:
            raw_pieces.append((piece_text, chapter, section, None))

    merged_pieces = _merge_small_chunks(raw_pieces)

    chunks = []
    for idx, (text, chapter, section, page) in enumerate(merged_pieces):
        chunks.append({
            "text": text,
            "chapter": chapter,
            "section": section,
            "page": page,
            "chunk_index": idx,
        })

    return chunks

MIN_CHUNK_CHARS = 150


def _merge_small_chunks(pieces: list[tuple]) -> list[tuple]:
    """
    Merges any chunk smaller than MIN_CHUNK_CHARS into the previous chunk,
    as long as they share the same chapter — regardless of whether they
    came from the same page or crossed a page boundary. Keeps the earlier
    chunk's page number (where the content primarily starts).
    """
    if not pieces:
        return pieces

    merged = [pieces[0]]
    for text, chapter, section, page in pieces[1:]:
        prev_text, prev_chapter, prev_section, prev_page = merged[-1]
        if len(text) < MIN_CHUNK_CHARS and chapter == prev_chapter:
            merged[-1] = (prev_text + "\n" + text, prev_chapter, prev_section, prev_page)
        else:
            merged.append((text, chapter, section, page))

    return merged

def _split_with_headings(text: str, current_chapter, current_section, heading_counts: dict):
    lines = text.split("\n")
    pieces = []
    buffer_lines = []
    buffer_chapter = current_chapter
    buffer_section = current_section

    def buffer_len():
        return sum(len(l) + 1 for l in buffer_lines)

    def flush():
        nonlocal buffer_lines, buffer_chapter, buffer_section
        piece_text = "\n".join(buffer_lines).strip()
        if piece_text:
            pieces.append((piece_text, buffer_chapter, buffer_section))
        buffer_lines = []

    for line in lines:
        ch_match = CHAPTER_PATTERN.match(line)
        if ch_match:
            # A new heading starts here — flush whatever was buffered under
            # the PREVIOUS heading first, so content never straddles a
            # unit/chapter boundary inside one chunk.
            if buffer_lines:
                flush()

            label_word = ch_match.group(1).title()
            heading_counts[label_word] = heading_counts.get(label_word, 0) + 1
            seq_index = heading_counts[label_word] - 1

            if seq_index < len(ROMAN_SEQUENCE):
                numeral = ROMAN_SEQUENCE[seq_index]
            else:
                numeral = ch_match.group(2).strip()

            current_chapter = f"{label_word} {numeral}"
            buffer_chapter = current_chapter
            buffer_section = current_section

        sec_match = SECTION_NUM_PATTERN.match(line)
        if sec_match:
            current_section = sec_match.group(1)
            buffer_section = current_section

        buffer_lines.append(line)

        if buffer_len() >= CHUNK_SIZE:
            piece_text = "\n".join(buffer_lines).strip()
            if piece_text:
                pieces.append((piece_text, buffer_chapter, buffer_section))
            overlap_text = piece_text[-CHUNK_OVERLAP:] if len(piece_text) > CHUNK_OVERLAP else piece_text
            buffer_lines = [overlap_text]

    flush()


    return pieces, current_chapter, current_section