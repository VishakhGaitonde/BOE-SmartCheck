import json
import re

from app.llm.gemini_client import call_gemini, extract_json, GeminiRateLimitError

VALID_STATUSES = {"SUPPORTED", "POTENTIALLY_UNRELATED", "REQUIRES_REVIEW"}
VALID_BLOOM = {"REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"}
VALID_ALIGNMENT = {"ALIGNED", "POTENTIAL_MISMATCH", "UNCERTAIN"}

# Search distance above this gets a "low score" note in the prompt.
LOW_CONFIDENCE_DISTANCE = 0.65

# Shared by both prompts below, so they always stay in sync.
_SUPPORT_RULES = """RULES FOR PART 1 (support), PER QUESTION:
- Use ONLY that question's own SYLLABUS EVIDENCE and TEXTBOOK EVIDENCE below, never your own knowledge and never another question's evidence.
- The evidence comes from a search system, so a passage can be off-topic even though it was returned. Judge each passage on its content. A low-score note only means "check that it is relevant"; it is not a reason to reject the passage.
- Judge the two sources separately, and be generous about what counts as a match:
  1. syllabus_match is true if the syllabus evidence lists the question's topic, a sub-topic of it, or a related topic heading, in the same subject. Different wording is fine, and a close or partial match counts.
  2. textbook_match is true if at least one textbook passage covers the main idea of the question, even if it covers only part of it, uses different wording, or explains the idea through an example. A close or partial match counts.
  A source is a mismatch only when its passages are about a different concept or a different subject, or nothing in them relates to the question. Common words such as design, process, system, model or analysis shared between two subjects are not a match on their own.
- The status follows strictly from the two flags:
  - both true -> SUPPORTED
  - exactly one true (syllabus matches but textbook does not, or textbook matches but syllabus does not) -> REQUIRES_REVIEW
  - both false -> POTENTIALLY_UNRELATED
"""

PROMPT_TEMPLATE = (
    "You are assisting a Board of Examinations (BOE) in verifying whether an exam question is supported by the prescribed syllabus and prescribed textbook.\n\n"
    + _SUPPORT_RULES
    + """
Respond with STRICT JSON ONLY — no markdown, no code fences, no extra commentary — matching exactly this schema:

{{
  "syllabus_match": true or false,
  "syllabus_topic": "<unit/topic matched from the syllabus evidence, or null>",
  "textbook_match": true or false,
  "textbook_reference": "<chapter/section/page matched from the textbook evidence, or null>",
  "status": "SUPPORTED" or "POTENTIALLY_UNRELATED" or "REQUIRES_REVIEW",
  "explanation": "<1-3 sentences grounded ONLY in the evidence above; name the subject of the question, of the syllabus evidence and of the textbook evidence>"
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
)

BATCH_PROMPT_TEMPLATE = (
    "You are assisting a Board of Examinations (BOE) with two checks on EACH of the following exam questions: (1) whether it is supported by the prescribed syllabus/textbook, and (2) its Bloom's Taxonomy level and CO alignment.\n\n"
    + _SUPPORT_RULES
    + """
RULES FOR PART 2 (CO/Bloom), PER QUESTION:
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
  "explanation": "<1-3 sentences, grounded only in that question's own evidence, naming the subject of the question and of the evidence>",
  "bloom_level": "REMEMBER" or "UNDERSTAND" or "APPLY" or "ANALYZE" or "EVALUATE" or "CREATE",
  "co_alignment": "ALIGNED" or "POTENTIAL_MISMATCH" or "UNCERTAIN",
  "co_bloom_explanation": "<1-2 sentences>"
}}

QUESTIONS:
{questions_block}
"""
)


def _apply_status_rule(r: dict) -> None:
    """Status follows strictly from the two match flags, when the model gave both."""
    s, t = r.get("syllabus_match"), r.get("textbook_match")
    if isinstance(s, bool) and isinstance(t, bool):
        if s and t:
            r["status"] = "SUPPORTED"
        elif s or t:
            r["status"] = "REQUIRES_REVIEW"
        else:
            r["status"] = "POTENTIALLY_UNRELATED"


def _strip_fences(text: str) -> str:
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
        if item.get("source"):
            meta_parts.append(item["source"])
        if item.get("chapter"):
            meta_parts.append(item["chapter"])
        if item.get("page") is not None:
            meta_parts.append(f"Page {item['page']}")
        meta_str = " | ".join(meta_parts) if meta_parts else "no metadata"
        distance = item.get("distance")
        note = ""
        if distance is not None and distance > LOW_CONFIDENCE_DISTANCE:
            note = " [low search score -- check that it is relevant]"
        lines.append(f"[{i}] ({meta_str}){note}\n{item['text'][:600]}")
    return "\n\n".join(lines)


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
        parsed = json.loads(_strip_fences(raw))
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
        _apply_status_rule(r)
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
        _apply_status_rule(result)
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