from app.llm.gemini_client import call_gemini, extract_json, GeminiRateLimitError

VALID_STATUSES = {"SUPPORTED", "POTENTIALLY_UNRELATED", "REQUIRES_REVIEW"}
VALID_BLOOM = {"REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"}
VALID_ALIGNMENT = {"ALIGNED", "POTENTIAL_MISMATCH", "UNCERTAIN"}

PROMPT_TEMPLATE = """You are assisting a Board of Examinations (BOE) with two checks on one exam question: (1) whether it is supported by the prescribed syllabus/textbook, and (2) its Bloom's Taxonomy level and CO alignment.

STRICT RULES FOR PART 1 (support):
- Use ONLY the SYLLABUS EVIDENCE and TEXTBOOK EVIDENCE below — never your own general knowledge.
- Judge support at the TOPIC level, not exact phrase match. A substantively relevant passage (even reworded) should lean SUPPORTED.
- REQUIRES_REVIEW only when evidence is genuinely thin or the specific concept can't be found. POTENTIALLY_UNRELATED only when there's no meaningful connection at all.

STRICT RULES FOR PART 2 (CO/Bloom):
- Determine Bloom's level from the question's own verb/phrasing.
- Judge CO alignment using ONLY the CO TEXT given below. If no CO text is given, set alignment to UNCERTAIN.

Respond with STRICT JSON ONLY, matching exactly this schema:
{{
  "syllabus_match": true or false,
  "syllabus_topic": "<topic matched, or null>",
  "textbook_match": true or false,
  "textbook_reference": "<chapter/section/page, or null>",
  "status": "SUPPORTED" or "POTENTIALLY_UNRELATED" or "REQUIRES_REVIEW",
  "explanation": "<1-3 sentences, grounded only in evidence>",
  "bloom_level": "REMEMBER" or "UNDERSTAND" or "APPLY" or "ANALYZE" or "EVALUATE" or "CREATE",
  "co_alignment": "ALIGNED" or "POTENTIAL_MISMATCH" or "UNCERTAIN",
  "co_bloom_explanation": "<1-2 sentences>"
}}

QUESTION:
{question_text}

CO CODE: {co_code}
CO TEXT: {co_text}

SYLLABUS EVIDENCE:
{syllabus_evidence}

TEXTBOOK EVIDENCE:
{textbook_evidence}
"""


def _format_evidence_block(items: list[dict]) -> str:
    if not items:
        return "(no evidence retrieved)"
    lines = []
    for i, item in enumerate(items, start=1):
        meta_parts = []
        if item.get("chapter"):
            meta_parts.append(item["chapter"])
        if item.get("page") is not None:
            meta_parts.append(f"Page {item['page']}")
        meta_str = " | ".join(meta_parts) if meta_parts else "no metadata"
        lines.append(f"[{i}] ({meta_str})\n{item['text'][:600]}")
    return "\n\n".join(lines)


def verify_and_analyze(question_text, co_code, co_text, syllabus_evidence, textbook_evidence) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        question_text=question_text,
        co_code=co_code or "(not specified)",
        co_text=co_text or "(not available)",
        syllabus_evidence=_format_evidence_block(syllabus_evidence),
        textbook_evidence=_format_evidence_block(textbook_evidence),
    )

    try:
        raw = call_gemini(prompt)
        result = extract_json(raw)
        result["llm_call_failed"] = False
    except GeminiRateLimitError as e:
        if e.is_daily_limit:
            raise
        result = _fallback(f"Rate-limited: {e}")
    except Exception as e:
        result = _fallback(f"Technical error: {e}")

    if result.get("status") not in VALID_STATUSES:
        result["status"] = "REQUIRES_REVIEW"
    if result.get("bloom_level") not in VALID_BLOOM:
        result["bloom_level"] = "UNDERSTAND"
    if result.get("co_alignment") not in VALID_ALIGNMENT:
        result["co_alignment"] = "UNCERTAIN"

    result.setdefault("syllabus_match", False)
    result.setdefault("syllabus_topic", None)
    result.setdefault("textbook_match", False)
    result.setdefault("textbook_reference", None)
    result.setdefault("explanation", "No explanation provided.")
    result.setdefault("co_bloom_explanation", "No explanation provided.")

    return result


def _fallback(msg: str) -> dict:
    return {
        "syllabus_match": False, "syllabus_topic": None,
        "textbook_match": False, "textbook_reference": None,
        "status": "REQUIRES_REVIEW", "explanation": f"{msg}. Manual BOE review required.",
        "bloom_level": "UNDERSTAND", "co_alignment": "UNCERTAIN",
        "co_bloom_explanation": f"{msg}.",
        "llm_call_failed": True,
    }