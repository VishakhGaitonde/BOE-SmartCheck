from app.llm.gemini_client import call_gemini, extract_json, GeminiRateLimitError

VALID_BLOOM_LEVELS = {"REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"}
VALID_ALIGNMENT = {"ALIGNED", "POTENTIAL_MISMATCH", "UNCERTAIN"}

PROMPT_TEMPLATE = """You are assisting a Board of Examinations (BOE) in checking a question's Bloom's Taxonomy cognitive level and its alignment with the course outcome (CO) it is tagged against.

STRICT RULES:
- Determine the Bloom's level based on the question's own verb/phrasing (e.g. "define/list" = Remember, "explain/describe" = Understand, "apply/solve" = Apply, "analyze/compare" = Analyze, "evaluate/justify" = Evaluate, "design/create" = Create).
- The CO TEXT below (if provided) is the only basis for judging alignment — do not assume what a CO "should" mean beyond what's given.
- If no CO text is provided, or it gives no clear cognitive-level expectation, set alignment to "UNCERTAIN" rather than guessing.
- Respond with STRICT JSON ONLY, matching exactly this schema:

{{
  "bloom_level": "REMEMBER" or "UNDERSTAND" or "APPLY" or "ANALYZE" or "EVALUATE" or "CREATE",
  "co_code": "<the CO code as given, or null>",
  "co_alignment": "ALIGNED" or "POTENTIAL_MISMATCH" or "UNCERTAIN",
  "explanation": "<1-2 sentence explanation>"
}}

QUESTION:
{question_text}

CO CODE (as extracted from the question paper): {co_code}

CO TEXT (from syllabus course outcomes, if matched): {co_text}
"""


def analyze_co_bloom(question_text: str, co_code: str | None, co_text: str | None) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        question_text=question_text,
        co_code=co_code or "(not specified)",
        co_text=co_text or "(not available)",
    )

    try:
        raw_response = call_gemini(prompt)
        result = extract_json(raw_response)
        result["llm_call_failed"] = False
    except GeminiRateLimitError as e:
        if e.is_daily_limit:
            raise
        return {
            "bloom_level": "UNDERSTAND", "co_code": co_code, "co_alignment": "UNCERTAIN",
            "explanation": f"LLM was rate-limited for this question ({e}).",
            "llm_call_failed": True,
        }
    except Exception as e:
        return {
            "bloom_level": "UNDERSTAND", "co_code": co_code, "co_alignment": "UNCERTAIN",
            "explanation": f"LLM call failed ({e}).",
            "llm_call_failed": True,
        }

    if result.get("bloom_level") not in VALID_BLOOM_LEVELS:
        result["bloom_level"] = "UNDERSTAND"
    if result.get("co_alignment") not in VALID_ALIGNMENT:
        result["co_alignment"] = "UNCERTAIN"

    result.setdefault("co_code", co_code)
    result.setdefault("explanation", "No explanation provided.")

    return result