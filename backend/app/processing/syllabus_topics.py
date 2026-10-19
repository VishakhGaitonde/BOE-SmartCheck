import re


def split_into_subtopics(text: str) -> list[str]:
    """
    Splits syllabus text into individual topic phrases (by sentence and
    colon-separated clause) instead of treating a whole unit/chunk as one
    blended blob. Shared by unit-mapping (Phase 9 optimization) and
    per-question retrieval, since both suffer the same dilution problem:
    a combined multi-topic embedding drowns out any single sub-topic that
    isn't semantically dominant in the blend.
    """
    lines = [l for l in text.split("\n") if l.strip() and not l.strip().startswith(("e ", "Unit"))]
    joined = " ".join(lines)

    raw_parts = re.split(r'[.:]\s+', joined)

    phrases = []
    for part in raw_parts:
        part = part.strip(" .,")
        if len(part) >= 15:
            phrases.append(part)

    return phrases if phrases else [text]