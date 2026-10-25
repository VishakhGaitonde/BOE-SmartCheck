def aggregate_paper_summary(marks_valid: bool, verification_results, co_bloom_results, duplication_results) -> dict:
    supported = sum(1 for v in verification_results if v.ai_status == "SUPPORTED")
    review = sum(1 for v in verification_results if v.ai_status == "REQUIRES_REVIEW")
    unrelated = sum(1 for v in verification_results if v.ai_status == "POTENTIALLY_UNRELATED")

    aligned = sum(1 for c in co_bloom_results if c.co_alignment == "ALIGNED")
    mismatch = sum(1 for c in co_bloom_results if c.co_alignment == "POTENTIAL_MISMATCH")
    uncertain = sum(1 for c in co_bloom_results if c.co_alignment == "UNCERTAIN")

    likely_dup = sum(1 for d in duplication_results if d.status == "LIKELY_DUPLICATE")
    possible_dup = sum(1 for d in duplication_results if d.status == "POSSIBLE_DUPLICATE")

    reasons = []
    if not marks_valid:
        reasons.append("Marks/section validation failed.")
    if unrelated > 0:
        reasons.append(f"{unrelated} question(s) flagged as potentially unrelated to the syllabus/textbook.")
    if review > 0:
        reasons.append(f"{review} question(s) require manual review for syllabus/textbook support.")
    if mismatch > 0:
        reasons.append(f"{mismatch} question(s) show a potential CO/Bloom-level mismatch.")
    if likely_dup > 0:
        reasons.append(f"{likely_dup} likely duplicate question pair(s) detected.")
    if possible_dup > 0:
        reasons.append(f"{possible_dup} possible duplicate question pair(s) detected.")

    return {
        "overall_status": "REQUIRES_BOE_REVIEW" if reasons else "SUPPORTED",
        "marks_valid": marks_valid,
        "supported_count": supported,
        "review_count": review,
        "unrelated_count": unrelated,
        "aligned_count": aligned,
        "mismatch_count": mismatch,
        "uncertain_count": uncertain,
        "likely_duplicate_count": likely_dup,
        "possible_duplicate_count": possible_dup,
        "reasons": reasons,
    }