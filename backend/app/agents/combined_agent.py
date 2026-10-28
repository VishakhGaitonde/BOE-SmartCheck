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

import json as _json

BATCH_PROMPT_TEMPLATE = """You are assisting a Board of Examinations (BOE) with two checks on EACH of the following exam questions: (1) whether it is supported by the prescribed syllabus/textbook, and (2) its Bloom's Taxonomy level and CO alignment.

STRICT RULES FOR PART 1 (support), PER QUESTION:
- Use ONLY that question's own SYLLABUS EVIDENCE and TEXTBOOK EVIDENCE below -- never your own general knowledge, and never another question's evidence.
- The evidence was retrieved by a search system and MAY be irrelevant even if it was returned -- a retrieval system always returns its "closest" matches even when nothing is actually close. Each evidence item is tagged with its retrieval confidence; treat LOW confidence items with real suspicion.
- Judge support by whether the evidence demonstrates the SAME SUBJECT DOMAIN and the SAME SPECIFIC CONCEPT as that question -- not by superficial word overlap. Two completely unrelated fields can share common words like "design", "process", "model", "system", "analysis", "characteristics", or "attributes" without being topically related at all. If the evidence is from a visibly different subject/domain than what the question asks about, this is POTENTIALLY_UNRELATED regardless of any shared vocabulary.
- Only mark SUPPORTED when the evidence genuinely explains or covers the specific concept that question asks about, in the correct subject domain, even if worded differently.
- REQUIRES_REVIEW is for cases where the evidence is in the RIGHT domain/topic area but doesn't fully/specifically cover what's asked -- not for cases where the domain itself doesn't match.
- POTENTIALLY_UNRELATED is for cases where the evidence's subject domain clearly does not match that question's subject at all, even if some words coincidentally overlap.
- Before deciding, explicitly check: "Is this evidence actually about the same subject this question is asking about?" If no, do not default to REQUIRES_REVIEW out of caution -- say POTENTIALLY_UNRELATED.

STRICT RULES FOR PART 2 (CO/Bloom), PER QUESTION:
- Determine Bloom's level from that question's own verb/phrasing.
- Judge CO alignment using ONLY that question's own CO TEXT. If no CO text is given for it, or it's from a clearly different subject than the question, set alignment to UNCERTAIN.

Respond with STRICT JSON ONLY — a JSON ARRAY with exactly {num_questions} objects, in the SAME ORDER as the questions below, each matching this schema:
{{
  "index": <the question's index number as given below>,
  "syllabus_match": true or false,
  "syllabus_topic": "<topic matched, or null>",
  "textbook_match": true or false,
  "textbook_reference": "<chapter/section/page, or null>",
  "status": "SUPPORTED" or "POTENTIALLY_UNRELATED" or "REQUIRES_REVIEW",
  "explanation": "<1-3 sentences, grounded only in that question's own evidence, explicitly naming the subject domain of both the question and the evidence>",
  "bloom_level": "REMEMBER" or "UNDERSTAND" or "APPLY" or "ANALYZE" or "EVALUATE" or "CREATE",
  "co_alignment": "ALIGNED" or "POTENTIAL_MISMATCH" or "UNCERTAIN",
  "co_bloom_explanation": "<1-2 sentences>"
}}

QUESTIONS:
{questions_block}
"""

def _format_question_block(index: int, question_text, co_code, co_text, syllabus_evidence, textbook_evidence) -> str:
    return f"""--- QUESTION INDEX {index} ---
QUESTION TEXT: {question_text}
CO CODE: {co_code or "(not specified)"}
CO TEXT: {co_text or "(not available)"}
SYLLABUS EVIDENCE:
{_format_evidence_block(syllabus_evidence)}
TEXTBOOK EVIDENCE:
{_format_evidence_block(textbook_evidence)}
"""


def verify_and_analyze_batch(items: list[dict]) -> list[dict]:
    """
    items: [{"index": int, "question_text": str, "co_code": str|None,
              "co_text": str|None, "syllabus_evidence": list, "textbook_evidence": list}]
    Returns a list of result dicts in the SAME order as `items` (matched by
    'index', not just position, to guard against the model reordering).
    One Gemini call handles the whole batch instead of one call per question.
    """
    questions_block = "\n".join(
        _format_question_block(
            it["index"], it["question_text"], it["co_code"], it["co_text"],
            it["syllabus_evidence"], it["textbook_evidence"],
        )
        for it in items
    )
    prompt = BATCH_PROMPT_TEMPLATE.format(num_questions=len(items), questions_block=questions_block)

    try:
        raw = call_gemini(prompt)
        parsed = _json.loads(_strip_fences(raw))
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON array")
    except GeminiRateLimitError as e:
        if e.is_daily_limit:
            raise
        return [_fallback(f"Rate-limited: {e}") for _ in items]
    except Exception as e:
        return [_fallback(f"Technical error: {e}") for _ in items]

    by_index = {r.get("index"): r for r in parsed if isinstance(r, dict)}

    results = []
    for it in items:
        r = by_index.get(it["index"])
        if r is None:
            results.append(_fallback("Model did not return a result for this question in the batch."))
            continue

        r["llm_call_failed"] = False
        if r.get("status") not in VALID_STATUSES:
            r["status"] = "REQUIRES_REVIEW"
        if r.get("bloom_level") not in VALID_BLOOM:
            r["bloom_level"] = "UNDERSTAND"
        if r.get("co_alignment") not in VALID_ALIGNMENT:
            r["co_alignment"] = "UNCERTAIN"
        r.setdefault("syllabus_match", False)
        r.setdefault("syllabus_topic", None)
        r.setdefault("textbook_match", False)
        r.setdefault("textbook_reference", None)
        r.setdefault("explanation", "No explanation provided.")
        r.setdefault("co_bloom_explanation", "No explanation provided.")
        results.append(r)

    return results


def _strip_fences(text: str) -> str:
    import re
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text

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
        distance = item.get("distance")
        confidence_note = ""
        if distance is not None:
            if distance > 0.6:
                confidence_note = " [LOW retrieval confidence -- this passage may not actually be relevant, do not assume it is just because it was retrieved]"
            elif distance > 0.4:
                confidence_note = " [MODERATE retrieval confidence]"
        lines.append(f"[{i}] ({meta_str}){confidence_note}\n{item['text'][:600]}")
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