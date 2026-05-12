"""Semantic Scholar collector.

Uses the Semantic Scholar Academic Graph API (https://api.semanticscholar.org/graph/v1).
API key is optional but increases rate limits significantly.
"""

import logging
from collections.abc import Generator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1"
_PAGE_SIZE = 100  # S2 maximum per bulk request
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
            batch_limit = min(_PAGE_SIZE, max_results - yielded)
            data = self._fetch_page(
                query=keyword,
                fields=_PAPER_FIELDS,
                limit=batch_limit,
                offset=offset,
                year=year_filter,
            )
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
        if not paper_ids:
            return []
        try:
            resp = self._client.post(
                "/paper/batch",
                json={"ids": paper_ids[:500]},
                params={"fields": _PAPER_FIELDS},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("S2 bulk fetch failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
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
