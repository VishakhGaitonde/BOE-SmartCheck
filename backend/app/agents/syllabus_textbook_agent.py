from app.llm.gemini_client import call_gemini, extract_json, GeminiRateLimitError

VALID_STATUSES = {"SUPPORTED", "POTENTIALLY_UNRELATED", "REQUIRES_REVIEW"}

PROMPT_TEMPLATE = """You are assisting a Board of Examinations (BOE) in verifying whether an exam question is supported by the prescribed syllabus and prescribed textbook.

STRICT RULES:
- Use ONLY the SYLLABUS EVIDENCE and TEXTBOOK EVIDENCE provided below to make your decision.
- Do NOT use your own general knowledge of the subject to decide whether the question belongs to the course — the evidence below is the only source of truth.
- Judge support at the TOPIC level, not by requiring an exact phrase-for-phrase match. If the evidence substantively covers the concept the question asks about — even using different wording, a broader passage, or a related example — treat it as supporting evidence. A partial or indirect but genuinely relevant connection should lean toward SUPPORTED, not REQUIRES_REVIEW.
- Reserve REQUIRES_REVIEW for cases where the evidence is genuinely thin, tangential, or you cannot find the specific concept addressed at all — not merely because the wording differs from the question.
- Reserve POTENTIALLY_UNRELATED for cases where the evidence shows no meaningful connection to the question's topic whatsoever.
- Respond with STRICT JSON ONLY — no markdown, no code fences, no extra commentary — matching exactly this schema:

{{
  "syllabus_match": true or false,
  "syllabus_topic": "<unit/topic matched from the syllabus evidence, or null>",
  "textbook_match": true or false,
  "textbook_reference": "<chapter/section/page matched from the textbook evidence, or null>",
  "status": "SUPPORTED" or "POTENTIALLY_UNRELATED" or "REQUIRES_REVIEW",
  "explanation": "<1-3 sentence explanation grounded ONLY in the evidence above>"
}}

QUESTION:
{question_text}

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
        if item.get("section"):
            meta_parts.append(f"Section {item['section']}")
        if item.get("page") is not None:
            meta_parts.append(f"Page {item['page']}")
        meta_str = " | ".join(meta_parts) if meta_parts else "no metadata"
        snippet = item["text"][:600]
        lines.append(f"[{i}] ({meta_str})\n{snippet}")
    return "\n\n".join(lines)


def verify_question(question_text: str, syllabus_evidence: list[dict], textbook_evidence: list[dict]) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        question_text=question_text,
        syllabus_evidence=_format_evidence_block(syllabus_evidence),
        textbook_evidence=_format_evidence_block(textbook_evidence),
    )

    try:
        raw_response = call_gemini(prompt)
        result = extract_json(raw_response)
        result["llm_call_failed"] = False
    except GeminiRateLimitError as e:
        if e.is_daily_limit:
            raise
        return {
            "syllabus_match": False, "syllabus_topic": None,
            "textbook_match": False, "textbook_reference": None,
            "status": "REQUIRES_REVIEW",
            "explanation": f"LLM was rate-limited for this question ({e}). Manual BOE review required.",
            "llm_call_failed": True,
        }
    except Exception as e:
        return {
            "syllabus_match": False, "syllabus_topic": None,
            "textbook_match": False, "textbook_reference": None,
            "status": "REQUIRES_REVIEW",
            "explanation": f"LLM verification failed due to a technical error ({e}). Manual BOE review required.",
            "llm_call_failed": True,
        }

    if result.get("status") not in VALID_STATUSES:
        result["status"] = "REQUIRES_REVIEW"
        result["explanation"] = (result.get("explanation") or "") + " (Model returned an invalid status; defaulted to REQUIRES_REVIEW.)"

    result.setdefault("syllabus_match", False)
    result.setdefault("syllabus_topic", None)
    result.setdefault("textbook_match", False)
    result.setdefault("textbook_reference", None)
    result.setdefault("explanation", "No explanation provided.")

    return result