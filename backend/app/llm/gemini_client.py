import json
import re
import time

import google.generativeai as genai

from app.config import settings

_configured = False
MODEL_NAME = "gemini-flash-lite-latest"

# Free tier is commonly 5 requests/minute — space calls out proactively
# to avoid reactively hitting 429s on every other question.
PROACTIVE_DELAY_SECONDS = 5.0


class GeminiRateLimitError(Exception):
    def __init__(self, message, retry_after_seconds=None, is_daily_limit=False):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.is_daily_limit = is_daily_limit


def _ensure_configured():
    global _configured
    if not _configured:
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not set in .env")
        genai.configure(api_key=settings.llm_api_key)
        _configured = True


def _parse_retry_delay(error_text: str):
    match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', error_text)
    if match:
        return int(match.group(1))
    match2 = re.search(r'retry in ([\d.]+)s', error_text)
    if match2:
        return float(match2.group(1))
    return None


def call_gemini(prompt: str, max_retries: int = 2, retry_delay_seconds: float = 3.0) -> str:
    _ensure_configured()
    model = genai.GenerativeModel(MODEL_NAME)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            return response.text
        except Exception as e:
            last_error = e
            error_text = str(e)
            is_rate_limit = "429" in error_text or "quota" in error_text.lower() or "ResourceExhausted" in type(e).__name__

            if is_rate_limit:
                parsed_delay = _parse_retry_delay(error_text)
                is_daily = "PerDay" in error_text

                if is_daily or (parsed_delay and parsed_delay > 60):
                    # Daily quota exhausted — retrying now is pointless and just
                    # wastes time; surface this immediately so the caller can
                    # stop processing the rest of the batch instead of failing
                    # every remaining question one by one.
                    raise GeminiRateLimitError(
                        f"Daily quota exhausted (retry after {parsed_delay or 'unknown'}s).",
                        retry_after_seconds=parsed_delay,
                        is_daily_limit=True,
                    ) from e

                if attempt < max_retries:
                    wait_time = (parsed_delay or retry_delay_seconds * (attempt + 1)) + 0.5
                    time.sleep(wait_time)
                    continue

                raise GeminiRateLimitError(
                    f"Per-minute rate limit hit repeatedly (retry after {parsed_delay or 'unknown'}s).",
                    retry_after_seconds=parsed_delay,
                    is_daily_limit=False,
                ) from e

            if attempt < max_retries:
                time.sleep(retry_delay_seconds * (attempt + 1))

    raise RuntimeError(f"Gemini call failed after {max_retries + 1} attempts: {last_error}")


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)