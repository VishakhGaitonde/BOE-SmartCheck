import re

CO_LINE_PATTERN = re.compile(r'^\s*(\d{1,2})\.\s*(.+)')
CO_HEADING_PATTERN = re.compile(r'Course\s+Outcomes?\s*\(?COs?\)?', re.IGNORECASE)


def extract_course_outcomes(syllabus_text: str) -> dict[str, str]:
    match = CO_HEADING_PATTERN.search(syllabus_text)
    if not match:
        return {}

    section_text = syllabus_text[match.end():]
    lines = section_text.split("\n")

    co_map = {}
    co_index = 0

    for line in lines:
        m = CO_LINE_PATTERN.match(line.strip())
        if m:
            co_index += 1
            co_text = m.group(2).strip()
            co_map[f"CO{co_index}"] = co_text
            if co_index >= 10:
                break

    return co_map