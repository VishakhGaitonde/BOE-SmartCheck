import re

SECTION_PATTERN = re.compile(r'^\s*(SECTION|PART)[\s\-:]*([A-E])\b', re.IGNORECASE)
OR_PATTERN = re.compile(r'^\s*OR\s*$', re.IGNORECASE)
QUESTION_NUM_PATTERN = re.compile(r'^\s*(?:Q\.?\s*)?(\d{1,2})\s*([a-eA-E])?\s*[\.\)]\s*(.*)')
MARKS_PATTERN = re.compile(
    r'\[(\d{1,3})\]|\((\d{1,3})\s*(?:marks?|m)\)|(\d{1,3})\s*marks?\b',
    re.IGNORECASE,
)


def parse_question_paper(text: str) -> list[dict]:
    """
    Best-effort deterministic parser for common SEE paper formats:
    'Q1.', '1.', '1 a)', 'SECTION A', 'OR', trailing [marks]/(marks)/N marks.
    Formats that deviate heavily may need manual correction via the UI —
    this is a starting structural pass, not a guarantee of 100% accuracy.
    """
    lines = [l for l in text.split("\n") if l.strip()]
    questions = []
    current_section = None
    i = 0

    while i < len(lines):
        line = lines[i]

        sec_match = SECTION_PATTERN.match(line)
        if sec_match:
            current_section = sec_match.group(2).upper()
            i += 1
            continue

        if OR_PATTERN.match(line):
            i += 1
            continue

        q_match = QUESTION_NUM_PATTERN.match(line)
        if q_match:
            number, sub, rest = q_match.group(1), q_match.group(2) or "", q_match.group(3).strip()

            j = i + 1
            full_text = rest
            while j < len(lines):
                nxt = lines[j]
                if QUESTION_NUM_PATTERN.match(nxt) or SECTION_PATTERN.match(nxt) or OR_PATTERN.match(nxt):
                    break
                full_text += " " + nxt.strip()
                j += 1

            marks = None
            m = MARKS_PATTERN.search(full_text)
            if m:
                marks = int(next(g for g in m.groups() if g))
                full_text = MARKS_PATTERN.sub("", full_text).strip()

            questions.append({
                "number": f"{number}{sub}" if sub else number,
                "text": full_text.strip(),
                "marks": marks,
                "section": current_section,
            })
            i = j
            continue

        i += 1

    return questions