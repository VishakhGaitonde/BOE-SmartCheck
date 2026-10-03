# Configurable section rules per SEE pattern.
# 100-mark pattern is fixed by the spec: A-E, 20 marks each.
# 50-mark pattern defaults to the same structure at half marks (A-E, 10 each) —
# adjust SECTION_PATTERNS below if your institution uses a different 50-mark layout.

import re


SECTION_PATTERNS = {
    "100": {"A": 20, "B": 20, "C": 20, "D": 20, "E": 20},
    "50": {"A": 10, "B": 10, "C": 10, "D": 10, "E": 10},
}


def validate_marks(questions: list[dict], pattern: str) -> dict:
    """
    questions: list of dicts with keys: question_number, marks, section
    pattern: "50" or "100"

    Returns a structured validation result — no LLM involved.
    """
    if pattern not in SECTION_PATTERNS:
        raise ValueError(f"Unknown pattern: {pattern}")

    expected_sections = SECTION_PATTERNS[pattern]
    expected_total = sum(expected_sections.values())

    # Sum marks per section from actual parsed questions
    actual_sections = {sec: 0.0 for sec in expected_sections}
    unassigned_questions = []
    missing_marks_questions = []

    for q in questions:
        section = q.get("section")
        marks = q.get("marks")

        if marks is None:
            missing_marks_questions.append(q.get("question_number"))
            continue

        if section not in expected_sections:
            unassigned_questions.append({
                "question_number": q.get("question_number"),
                "section": section,
                "marks": marks,
            })
            continue

        actual_sections[section] += marks

    section_results = []
    issues = []

    for sec, expected in expected_sections.items():
        actual = actual_sections[sec]
        is_valid = actual == expected
        section_results.append({
            "section": sec,
            "expected_marks": expected,
            "actual_marks": actual,
            "valid": is_valid,
        })
        if not is_valid:
            issues.append(
                f"Section {sec}: expected {expected} marks, found {actual}."
            )

    calculated_total = sum(actual_sections.values())
    total_valid = calculated_total == expected_total
    if not total_valid:
        issues.append(
            f"Total marks mismatch: expected {expected_total}, calculated {calculated_total}."
        )

    if missing_marks_questions:
        issues.append(
            f"{len(missing_marks_questions)} question(s) had no detected marks: "
            f"{', '.join(str(q) for q in missing_marks_questions)}."
        )

    if unassigned_questions:
        issues.append(
            f"{len(unassigned_questions)} question(s) could not be matched to a known section."
        )

    overall_valid = total_valid and all(s["valid"] for s in section_results) and not missing_marks_questions and not unassigned_questions

    return {
        "pattern": pattern,
        "expected_total_marks": expected_total,
        "calculated_total_marks": calculated_total,
        "sections": section_results,
        "missing_marks_questions": missing_marks_questions,
        "unassigned_questions": unassigned_questions,
        "overall_valid": overall_valid,
        "issues": issues,
    }



def validate_unit_or_pattern(questions: list[dict], total_marks: float, num_units: int = 5) -> dict:
    """
    For the common 'UNIT I-V, answer one full question per unit (OR choice)'
    pattern. Each unit must contain exactly 2 alternative full questions,
    each summing to total_marks / num_units.
    """
    if num_units <= 0 or total_marks % num_units != 0:
        raise ValueError("total_marks must be evenly divisible by num_units")

    marks_per_unit = total_marks / num_units
    units: dict[str, dict[str, float]] = {}
    missing_marks = []
    unassigned = []

    for q in questions:
        section = q.get("section")
        marks = q.get("marks")
        number = q.get("question_number")

        main_num_match = re.match(r"^(\d+)", str(number))
        main_num = main_num_match.group(1) if main_num_match else str(number)

        if marks is None:
            missing_marks.append(number)
            continue
        if not section or not str(section).upper().startswith("UNIT"):
            unassigned.append({"question_number": number, "section": section, "marks": marks})
            continue

        units.setdefault(section, {}).setdefault(main_num, 0.0)
        units[section][main_num] += marks

    unit_results = []
    issues = []

    for unit_label, full_qs in units.items():
        for main_num, total in full_qs.items():
            valid = total == marks_per_unit
            unit_results.append({
                "unit": unit_label,
                "question_number": main_num,
                "expected_marks": marks_per_unit,
                "actual_marks": total,
                "valid": valid,
            })
            if not valid:
                issues.append(f"{unit_label} Q{main_num}: expected {marks_per_unit} marks, found {total}.")

        if len(full_qs) != 2:
            issues.append(f"{unit_label}: expected 2 alternative full questions (OR), found {len(full_qs)}.")

    if missing_marks:
        issues.append(f"{len(missing_marks)} question(s) had no detected marks: {', '.join(str(m) for m in missing_marks)}.")
    if unassigned:
        issues.append(f"{len(unassigned)} question(s) could not be matched to a known unit.")

    # Real paper total = one alternative per unit, not all alternatives summed.
    # Count each unit once, using its expected marks_per_unit if that unit's
    # structure is valid, otherwise fall back to its first alternative's actual marks.
    calculated_total = 0.0
    for unit_label, full_qs in units.items():
        if full_qs:
            # Use the first alternative's marks as the "answered" contribution
            first_marks = next(iter(full_qs.values()))
            calculated_total += first_marks

    return {
        "structure_type": "UNIT_OR",
        "total_expected_marks": total_marks,
        "marks_per_unit": marks_per_unit,
        "calculated_total_marks": calculated_total,
        "unit_results": unit_results,
        "missing_marks_questions": missing_marks,
        "unassigned_questions": unassigned,
        "overall_valid": not issues,
        "issues": issues,
    }