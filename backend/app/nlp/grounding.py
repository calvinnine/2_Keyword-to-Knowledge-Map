"""External grounding for LLM translation candidates.

Two lookups, both best-effort (graceful degradation on failure / timeout):

1. OpenAlex exact-phrase works count
   - Endpoint: GET /works?filter=title_and_abstract.search:"<term>"&per-page=1
   - Returns meta.count = number of OA papers whose title/abstract contains
     the term as a literal phrase. Updated daily.
   - This catches LLM hallucinations (count = 0) and outdated translations
     (count very small for terms that should be common). It also gives the
     UI a useful relevance signal ("OA: 12K papers").
   - We deliberately avoid /autocomplete/concepts because OA froze the
     concepts taxonomy in 2023, so it misses post-2023 terms entirely.

2. Korean Wikipedia → English Wikipedia interlanguage link
   - Endpoint: GET ko.wikipedia.org/w/api.php?action=query&prop=langlinks
   - Wikipedia editors curate ko↔en mappings by hand, so this catches
     terms that the LLM (training cutoff ~2024 mid) may not know yet
     — e.g. "에이전틱 AI" → "Agentic AI".
   - Only relevant when the original user input contains Hangul.

Both lookups run in parallel via a thread pool to keep total latency low.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_OA_WORKS_URL = "https://api.openalex.org/works"
_WIKI_KO_API = "https://ko.wikipedia.org/w/api.php"
_HTTP_TIMEOUT = 8.0     # per-call timeout
_MAX_PARALLEL = 3       # OA tolerates ~5 req/s polite — keep concurrency low
_RETRY_ON_FAIL = 1      # one extra attempt per term on transient failure


class TermInfo(TypedDict, total=False):
    """Per-term grounding metadata, attached to a search term in the UI."""
    oa_works_count: int     # OA papers matching this term as an exact phrase
    source: str             # 'llm' (default) | 'wikipedia'


# ---------------------------------------------------------------------------
# OpenAlex exact-phrase works count
# ---------------------------------------------------------------------------

def _oa_default_params() -> dict[str, str]:
    """Polite-pool email, identical to OpenAlexCollector."""
    params: dict[str, str] = {}
    if settings.openalex_email:
        params["mailto"] = settings.openalex_email
    return params


def validate_term_with_oa(term: str) -> TermInfo | None:
    """Return number of OA works matching *term* as an exact phrase.

    Returns ``{"oa_works_count": N}`` (N may be 0) or ``None`` if the call
    fails after _RETRY_ON_FAIL+1 attempts.
    """
    if not term or not term.strip():
        return None
    # title_and_abstract.search wants a quoted string for phrase matching.
    phrase = '"' + term.strip().replace('"', "") + '"'
    last_exc: Exception | None = None
    for attempt in range(_RETRY_ON_FAIL + 1):
        try:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                r = client.get(
                    _OA_WORKS_URL,
                    params={
                        **_oa_default_params(),
                        "filter": f"title_and_abstract.search:{phrase}",
                        "per-page": "1",
                        "select": "id",  # minimal payload
                    },
                )
                r.raise_for_status()
                data = r.json()
                count = int((data.get("meta") or {}).get("count") or 0)
                return TermInfo(oa_works_count=count)
        except Exception as exc:
            last_exc = exc
            # Don't sleep on the final attempt
            if attempt < _RETRY_ON_FAIL:
                import time
                time.sleep(0.5)
    logger.debug("OA works-count failed for %r after %d attempts: %s",
                 term, _RETRY_ON_FAIL + 1, last_exc)
    return None


def validate_terms_bulk(terms: list[str]) -> dict[str, TermInfo]:
    """Validate a list of terms in parallel against OA. Best-effort.

    Each term is validated independently — partial failures don't drop
    other terms. A per-term timeout of _HTTP_TIMEOUT keeps the overall
    latency bounded even if one OA call hangs.
    """
    out: dict[str, TermInfo] = {}
    if not terms:
        return out
    # Overall budget: allow up to ~3× per-term timeout for the whole batch
    # so a slow term doesn't poison the others.
    overall_timeout = _HTTP_TIMEOUT * 3
    with ThreadPoolExecutor(max_workers=_MAX_PARALLEL) as pool:
        future_to_term = {pool.submit(validate_term_with_oa, t): t for t in terms}
        try:
            for future in as_completed(future_to_term, timeout=overall_timeout):
                term = future_to_term[future]
                try:
                    v = future.result(timeout=0)  # already completed
                    if v is not None:
                        out[term] = v
                except Exception as exc:
                    logger.debug("OA validate worker failed for %r: %s", term, exc)
        except TimeoutError:
            # Batch-level timeout — collect whatever finished without re-raising
            for fut, term in future_to_term.items():
                if fut.done() and term not in out:
                    try:
                        v = fut.result(timeout=0)
                        if v is not None:
                            out[term] = v
                    except Exception:
                        pass
            logger.info("validate_terms_bulk: %d/%d completed within %.0fs",
                        len(out), len(terms), overall_timeout)
    return out


# ---------------------------------------------------------------------------
# Wikipedia interlanguage links
# ---------------------------------------------------------------------------

def lookup_wiki_langlink(korean_term: str) -> str | None:
    """Resolve a Korean Wikipedia title to its English Wikipedia title.

    Returns the English title (e.g. "Agentic AI") or ``None`` if no
    Korean article exists, or it has no English langlink, or the API call
    fails. Follows redirects.
    """
    if not korean_term or not korean_term.strip():
        return None
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            r = client.get(
                _WIKI_KO_API,
                params={
                    "action": "query",
                    "prop": "langlinks",
                    "titles": korean_term.strip(),
                    "lllang": "en",
                    "format": "json",
                    "redirects": 1,
                },
                headers={
                    # Wikipedia asks for a descriptive User-Agent.
                    "User-Agent": "K2KM/0.1 (https://github.com/local; contact: dev@local)",
                },
            )
            r.raise_for_status()
            pages = (r.json().get("query") or {}).get("pages") or {}
            for _, page in pages.items():
                # If the page itself doesn't exist, the API returns pageid=-1
                # under a placeholder. langlinks is only present on real pages.
                links = page.get("langlinks") or []
                if links:
                    title = links[0].get("*", "").strip()
                    return title or None
            return None
    except Exception as exc:
        logger.debug("Wiki langlink failed for %r: %s", korean_term, exc)
        return None
