"""Semantic Scholar collector.

Uses the Semantic Scholar Academic Graph API (https://api.semanticscholar.org/graph/v1).
API key is optional but increases rate limits significantly.
"""

import logging
from collections.abc import Generator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1"
_PAGE_SIZE = 100  # S2 maximum per bulk request
_S2_MAX_RESULTS = 1000  # S2 paper/search hard cap: offset + limit <= 1000
_PAPER_FIELDS = (
    "paperId,externalIds,title,abstract,year,publicationDate,"
    "venue,publicationVenue,publicationTypes,"
    "authors,citations.paperId,references.paperId,"
    "fieldsOfStudy,s2FieldsOfStudy,"
    "citationCount,referenceCount,isOpenAccess"
)


class SemanticScholarCollector(BaseCollector):
    def __init__(self) -> None:
        headers: dict[str, str] = {}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key
        self._client = httpx.Client(
            base_url=_BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(
        self,
        keyword: str,
        max_results: int,
        year_start: int | None = None,
        year_end: int | None = None,
        **kwargs: Any,
    ) -> Generator[dict, None, None]:
        """Yield raw S2 paper dicts up to max_results."""
        yielded = 0
        offset = 0

        year_filter: str | None = None
        if year_start and year_end:
            year_filter = f"{year_start}-{year_end}"
        elif year_start:
            year_filter = f"{year_start}-"
        elif year_end:
            year_filter = f"-{year_end}"

        while yielded < max_results:
            # S2 paper/search hard cap: offset + limit must be <= 1000.
            if offset >= _S2_MAX_RESULTS:
                logger.info(
                    "S2 paper/search offset cap reached (%d); stopping at %d papers",
                    _S2_MAX_RESULTS, yielded,
                )
                break
            batch_limit = min(_PAGE_SIZE, max_results - yielded, _S2_MAX_RESULTS - offset)
            try:
                data = self._fetch_page(
                    query=keyword,
                    fields=_PAPER_FIELDS,
                    limit=batch_limit,
                    offset=offset,
                    year=year_filter,
                )
            except httpx.HTTPStatusError as exc:
                # 400 commonly means we hit the offset cap with a residual query;
                # don't fail the whole job — just stop paging.
                if exc.response.status_code == 400:
                    logger.warning("S2 paper/search 400 at offset=%d; stopping", offset)
                    break
                raise
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                if yielded >= max_results:
                    return
                yield item
                yielded += 1

            offset += len(items)
            if not data.get("next"):
                break

        logger.info("S2 collected %d papers for keyword=%r", yielded, keyword)

    def get_paper(self, source_id: str) -> dict | None:
        """Fetch a single paper by S2 paperId."""
        try:
            resp = self._client.get(
                f"/paper/{source_id}",
                params={"fields": _PAPER_FIELDS},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("S2 get_paper failed for %s: %s", source_id, exc)
            return None

    def get_papers_bulk(self, paper_ids: list[str]) -> list[dict]:
        """Fetch up to 500 papers by S2 paperIds in a single POST."""
        return self.get_papers_bulk_with_fields(paper_ids, _PAPER_FIELDS)

    def get_papers_bulk_with_fields(
        self, paper_ids: list[str], fields: str
    ) -> list[dict]:
        """Fetch up to 500 papers in batch with custom `fields` selection.

        Used by citation_enrichment to request `citations.publicationTypes`
        without paying the cost of the full paper payload. Retries on 429
        (rate limit) so Celery worker concurrency doesn't silently miss data.
        """
        if not paper_ids:
            return []

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=2, min=4, max=60),
            retry=retry_if_exception_type(httpx.HTTPStatusError),
            reraise=False,
        )
        def _do_fetch() -> list[dict]:
            resp = self._client.post(
                "/paper/batch",
                json={"ids": paper_ids[:500]},
                params={"fields": fields},
            )
            if resp.status_code == 429:
                # Surface to tenacity so it backs off and retries.
                raise httpx.HTTPStatusError(
                    "S2 429 rate limit", request=resp.request, response=resp
                )
            resp.raise_for_status()
            return resp.json()

        try:
            return _do_fetch()
        except Exception as exc:
            logger.warning("S2 bulk fetch gave up after retries: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        # S2 free tier rate limit (~1 req/s) can stall for 30-60s under load,
        # especially when multiple jobs / multi-keyword expansion hits in parallel.
        # 7 attempts × exp backoff (4 → 60s) gives ~3 min total before giving up.
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )
    def _fetch_page(
        self,
        query: str,
        fields: str,
        limit: int,
        offset: int,
        year: str | None,
    ) -> dict:
        params: dict[str, Any] = {
            "query": query,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }
        if year:
            params["year"] = year
        resp = self._client.get("/paper/search", params=params)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SemanticScholarCollector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
