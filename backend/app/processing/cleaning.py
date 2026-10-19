import re


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()

SYLLABUS_NOISE_PATTERNS = [
    re.compile(r'^e?\s*Pedagogy.*', re.IGNORECASE),
    re.compile(r'^e?\s*Links?:.*', re.IGNORECASE),
    re.compile(r'https?://\S+'),
]
SYLLABUS_CUTOFF_MARKERS = ["Text Books:", "Reference Books:", "Course Outcomes"]


def clean_syllabus_text(text: str) -> str:
    """
    Strips administrative boilerplate (Pedagogy/Links lines, and everything
    from 'Text Books:'/'Reference Books:'/'Course Outcomes' onward) that
    otherwise dilutes per-unit embedding quality — these lines are
    identical across every unit and add no topic-distinguishing signal,
    which was measurably hurting syllabus match distances.
    """
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(marker) for marker in SYLLABUS_CUTOFF_MARKERS):
            break  # stop entirely once back-matter starts
        if any(p.match(stripped) for p in SYLLABUS_NOISE_PATTERNS):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)