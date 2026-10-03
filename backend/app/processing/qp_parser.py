import re

UNIT_PATTERN = re.compile(r'^\s*UNIT\s*[-–:]*\s*([IVXLC\d]+)\b', re.IGNORECASE)
SECTION_PATTERN = re.compile(r'^\s*(SECTION|PART)[\s\-:]*([A-E])\b', re.IGNORECASE)
OR_PATTERN = re.compile(r'^\s*OR\s*$', re.IGNORECASE)

MAIN_Q_PATTERN = re.compile(r'^\s*(\d{1,2})\s*[\.\)]\s*(.*)')
SUB_Q_PATTERN = re.compile(r'^\s*([a-eA-E])\s*[\.\)]\s*(.*)')

CO_PATTERN = re.compile(r'\bCO\s*-?\s*(\d{1,2})\b', re.IGNORECASE)

MARKS_PATTERN = re.compile(
    r'\[(\d{1,3})\]'
    r'|\((\d{1,3})\s*(?:marks?|m)?\)'
    r'|(\d{1,3})\s*marks?\b',
    re.IGNORECASE,
)

# Lines that are page furniture, not question content — stop/ignore these
NOISE_PATTERN = re.compile(
    r'^\s*(USN\b|Page\s+\d+\s+of\s+\d+|Created by trial version|\*{3,}|AL\d{2}\s*$)',
    re.IGNORECASE,
)


def parse_question_paper(text: str) -> list[dict]:
    lines = [l for l in text.split("\n") if l.strip() and not NOISE_PATTERN.match(l.strip())]
    questions = []
    current_group = None
    current_main_number = None
    i = 0

    while i < len(lines):
        line = lines[i]

        unit_match = UNIT_PATTERN.match(line)
        if unit_match:
            current_group = f"UNIT {unit_match.group(1).upper()}"
            i += 1
            continue

        sec_match = SECTION_PATTERN.match(line)
        if sec_match:
            current_group = f"SECTION {sec_match.group(2).upper()}"
            i += 1
            continue

        if OR_PATTERN.match(line):
            i += 1
            continue

        main_match = MAIN_Q_PATTERN.match(line)
        if main_match:
            current_main_number = main_match.group(1)
            rest = main_match.group(2).strip()

            inner_sub = SUB_Q_PATTERN.match(rest)
            if inner_sub:
                sub_letter, sub_text = inner_sub.group(1).lower(), inner_sub.group(2).strip()
                full_text, marks, co, j = _consume(lines, i + 1, sub_text)
                if full_text.strip():
                    questions.append({
                        "number": f"{current_main_number}{sub_letter}",
                        "text": full_text.strip(),
                        "marks": marks,
                        "section": current_group,
                        "co": co,
                    })
                i = j
            else:
                # Bare main number line ("1.") with no sub-part text yet on
                # this line — just a container header, don't emit a question.
                # If it DOES have real content (no sub-letter format used),
                # treat the main number itself as the question.
                full_text, marks, co, j = _consume(lines, i + 1, rest)
                if full_text.strip():
                    questions.append({
                        "number": current_main_number,
                        "text": full_text.strip(),
                        "marks": marks,
                        "section": current_group,
                        "co": co,
                    })
                i = j
            continue

        sub_match = SUB_Q_PATTERN.match(line)
        if sub_match and current_main_number is not None:
            sub_letter, sub_text = sub_match.group(1).lower(), sub_match.group(2).strip()
            full_text, marks, co, j = _consume(lines, i + 1, sub_text)
            if full_text.strip():
                questions.append({
                    "number": f"{current_main_number}{sub_letter}",
                    "text": full_text.strip(),
                    "marks": marks,
                    "section": current_group,
                    "co": co,
                })
            i = j
            continue

        i += 1

    return questions


def _consume(lines, start_idx, initial_text):
    full_text = initial_text
    j = start_idx
    while j < len(lines):
        nxt = lines[j]
        if (MAIN_Q_PATTERN.match(nxt) or SUB_Q_PATTERN.match(nxt)
                or UNIT_PATTERN.match(nxt) or SECTION_PATTERN.match(nxt)
                or OR_PATTERN.match(nxt)):
            break
        full_text += " " + nxt.strip()
        j += 1

    co = None
    co_match = CO_PATTERN.search(full_text)
    if co_match:
        co = f"CO{co_match.group(1)}"
        full_text = CO_PATTERN.sub("", full_text)

    marks = None
    m = MARKS_PATTERN.search(full_text)
    if m:
        marks = int(next(g for g in m.groups() if g))
        full_text = MARKS_PATTERN.sub("", full_text)

    full_text = re.sub(r'\s+', ' ', full_text).strip()

    return full_text, marks, co, j