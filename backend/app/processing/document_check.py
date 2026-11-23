import re

# Words ignored when comparing titles and course names.
_STOP = {"and", "the", "for", "with", "from", "edition", "edn"}

FRONT_CHARS = 8000        # how much of a textbook's start is searched for its title
MATCH_THRESHOLD = 0.6     # share of a listed entry's words found in the textbook
COURSE_THRESHOLD = 0.8    # share of the course-name words found in the syllabus


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _tokens(text):
    return [t for t in re.findall(r"[a-z]{3,}", _norm(text)) if t not in _STOP]


def _course_found(course, syllabus_text):
    if not _norm(course):
        return True  # nothing was entered, nothing to check
    if _norm(course) in _norm(syllabus_text):
        return True
    words = _tokens(course)
    if not words:
        return True
    present = set(_tokens(syllabus_text))
    return sum(w in present for w in words) / len(words) >= COURSE_THRESHOLD


def listed_textbooks(syllabus_text):
    """Entries under 'Text Books' (and 'Reference Books') in the syllabus."""
    start = re.search(r"text\s*books?", syllabus_text, re.I)
    if not start:
        return []
    section = syllabus_text[start.start():start.start() + 3000]
    end = re.search(r"course\s+outcomes?", section, re.I)
    if end:
        section = section[:end.start()]
    parts = re.split(r"(?m)^\s*\d{1,2}\s*[\.\)]\s*", section)
    entries = [" ".join(p.split()) for p in parts[1:] if p.strip()]
    entries = [re.sub(r"\s*reference\s*books?\s*:?\s*$", "", e, flags=re.I) for e in entries]
    return [e for e in entries if len(_tokens(e)) >= 4]


def _best_entry(textbook, entries):
    front = set(_tokens(f"{textbook.filename} {(textbook.extracted_text or '')[:FRONT_CHARS]}"))
    best, best_score = None, 0.0
    for entry in entries:
        words = _tokens(entry)
        score = sum(w in front for w in words) / len(words)
        if score > best_score:
            best, best_score = entry, score
    return best, best_score


def check_documents(course, syllabus, textbooks):
    text = syllabus.extracted_text or ""
    problems = []

    if not _course_found(course, text):
        problems.append({
            "kind": "syllabus", "filename": syllabus.filename,
            "message": f'The course name "{course}" was not found in this syllabus.',
        })

    entries = listed_textbooks(text)
    if not entries:
        problems.append({
            "kind": "syllabus", "filename": syllabus.filename,
            "message": 'No "Text Books" list was found in this syllabus, so the textbooks cannot be checked.',
        })
    else:
        for tb in textbooks:
            _, score = _best_entry(tb, entries)
            if score < MATCH_THRESHOLD:
                problems.append({
                    "kind": "textbook", "filename": tb.filename,
                    "message": "This textbook does not match any textbook listed in the syllabus.",
                })

    return {"ok": not problems, "problems": problems, "listed_textbooks": [e[:160] for e in entries]}