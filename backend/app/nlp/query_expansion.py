"""LLM-based query translation + expansion for academic paper search.

This module performs translation and expansion in a SINGLE LLM call so the
model has full domain context to disambiguate. For example, "큐빗" alone is
ambiguous (qubit? cubic?), but combined with "생성 및 유지" the model can
reason that "qubit generation/maintenance" is the intended technical sense.

Returns
-------
dict with:
  translated: str | None    — English form (None if input was already English)
  search_terms: list[str]   — ranked expanded terms (first = primary)

Graceful degradation
--------------------
If Groq is unavailable or fails, falls back to [input_keyword] without
translation.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TypedDict

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_INPUT_CHARS = 200
_TIMEOUT_SECONDS = 15.0
# 70b model — much better at Korean technical/academic disambiguation than 8b.
_MODEL = "llama-3.3-70b-versatile"

_HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")


class ExpansionResult(TypedDict):
    translated: str | None
    search_terms: list[str]


_SYSTEM_PROMPT = """\
You are an academic-search expert assisting researchers who search OpenAlex \
and Semantic Scholar. Given a (possibly Korean) keyword or short phrase \
describing a research topic, return a JSON object with two fields:

  {
    "translated": "<English form, or null if input is already English>",
    "search_terms": ["term1", "term2", ...]
  }

Rules for "translated":
- Use the canonical academic English term, not literal word-by-word translation.
- Preserve the DOMAIN of the input. Use surrounding words to disambiguate \
  technical jargon. Examples:
    "큐빗 생성"   → "qubit generation"           (NOT "cubic creation")
    "트랜스포머"  → "transformer model"          (NOT power transformer)
    "그래프"      → "graph neural network"       (if context implies ML)
- If the input is already English (no Korean), set "translated" to null.

Rules for "search_terms":
- 5 to 7 terms, ordered most specific → most general.
- English only.
- Each term 1-6 words, no duplicates or near-duplicates.
- Include: canonical name, common acronyms/abbreviations, important subtopics, \
  alternative phrasings seen in academic paper titles.
- Exclude generic words like "research", "study", "method".
- The first element should be the most direct/canonical version of the topic.

Return ONLY valid JSON. No markdown, no explanation, no code fences.

Example input: 양자 암호 통신
Example output:
{"translated": "quantum cryptography", "search_terms": ["quantum key distribution", "QKD", "quantum cryptography", "BB84 protocol", "post-quantum cryptography", "quantum secure communication"]}

Example input: foundation model
Example output:
{"translated": null, "search_terms": ["large language model", "foundation model", "LLM", "pre-trained transformer", "self-supervised pretraining"]}
"""


def contains_hangul(text: str | None) -> bool:
    return bool(text) and bool(_HANGUL_RE.search(text))


def translate_and_expand(keyword: str, max_terms: int = 6) -> ExpansionResult:
    """Translate (if Korean) and expand *keyword* in a single LLM call.

    Falls back to {translated: None, search_terms: [keyword]} on any error.
    """
    fallback: ExpansionResult = {"translated": None, "search_terms": [keyword]}

    if not keyword or not keyword.strip():
        return fallback

    if not settings.groq_api_key:
        logger.info("GROQ_API_KEY not set; returning single-term fallback for %r", keyword)
        return fallback

    trimmed = keyword.strip()[:_MAX_INPUT_CHARS]

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not available; skipping expansion")
        return fallback

    try:
        client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.insight_base_url,
            timeout=_TIMEOUT_SECONDS,
        )
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": trimmed},
            ],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()

        # Strip optional code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("LLM returned non-object")

        translated_raw = data.get("translated")
        translated: str | None = None
        if isinstance(translated_raw, str) and translated_raw.strip():
            translated = translated_raw.strip()

        candidates_raw = data.get("search_terms") or []
        if not isinstance(candidates_raw, list):
            raise ValueError("search_terms is not a list")

        # Normalise: trim, drop empties, deduplicate case-insensitively
        seen: set[str] = set()
        terms: list[str] = []
        for t in candidates_raw:
            if not isinstance(t, str):
                continue
            t = t.strip()
            if not t:
                continue
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            terms.append(t)

        if not terms:
            # Model returned no terms — fall back to translation (or input)
            terms = [translated or trimmed]

        terms = terms[:max_terms]
        result: ExpansionResult = {"translated": translated, "search_terms": terms}
        logger.info("Translate+expand %r → %s", trimmed, result)
        return result

    except Exception as exc:
        logger.warning("translate_and_expand failed (%s); falling back", exc)
        return fallback


# ---------------------------------------------------------------------------
# Backwards-compatible single-purpose wrappers
# ---------------------------------------------------------------------------

def expand_keywords(keyword: str, max_terms: int = 6) -> list[str]:
    """Return a list of related English search terms for *keyword*.

    Kept for compatibility with callers that don't need the translation
    breakdown. Use translate_and_expand() to get both pieces.
    """
    return translate_and_expand(keyword, max_terms=max_terms)["search_terms"]
