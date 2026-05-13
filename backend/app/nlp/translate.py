"""Korean → English keyword translation via Groq.

Used to normalise search keywords before hitting OpenAlex / Semantic Scholar,
both of which index almost exclusively English-language metadata.

If GROQ_API_KEY is missing or the call fails, the original text is returned
unchanged — callers should treat translation as best-effort.
"""

from __future__ import annotations

import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)

# Hangul syllables + Jamo. If a string contains any of these, it likely
# needs translation before being sent to English-only paper indexes.
_HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")

_MAX_INPUT_CHARS = 200  # keyword fields are short; cap defensively
_TIMEOUT_SECONDS = 8.0
_MODEL = "llama-3.1-8b-instant"


def contains_hangul(text: str | None) -> bool:
    return bool(text) and bool(_HANGUL_RE.search(text))


def translate_keyword_to_english(text: str) -> str:
    """Translate a Korean keyword/phrase to a concise English search term.

    Returns the input unchanged if:
      - no Hangul is present
      - Groq is not configured
      - the API call fails
    """
    if not text or not contains_hangul(text):
        return text
    if not settings.groq_api_key:
        logger.info("GROQ_API_KEY not set; skipping KO→EN translation for %r", text)
        return text

    trimmed = text.strip()[:_MAX_INPUT_CHARS]

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not available; skipping translation")
        return text

    system = (
        "You translate Korean research keywords or short natural-language "
        "questions into a concise English search term suitable for "
        "academic paper search engines (OpenAlex, Semantic Scholar). "
        "Return ONLY the English keyword/phrase — no quotes, no explanation, "
        "no punctuation at the end. Prefer the canonical English term used in "
        "academic literature. If the input is already English, return it "
        "unchanged. Keep it under 8 words."
    )

    try:
        client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.insight_base_url,
            timeout=_TIMEOUT_SECONDS,
        )
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": trimmed},
            ],
            temperature=0.0,
            max_tokens=40,
        )
        out = (resp.choices[0].message.content or "").strip()
        # Strip wrapping quotes / trailing punctuation the model sometimes adds
        out = out.strip('"\'` .,;:!?')
        if not out:
            return text
        logger.info("KO→EN translated %r → %r", text, out)
        return out
    except Exception as exc:
        logger.warning("KO→EN translation failed (%s); using original keyword", exc)
        return text
