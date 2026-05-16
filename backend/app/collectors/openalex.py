"""OpenAlex collector.

Uses the OpenAlex REST API (https://docs.openalex.org).
Polite-pool email is included in every request when configured.
Pagination is handled via cursor-based `cursor` parameter.
"""

import logging
from collections.abc import Generator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openalex.org"
_PAGE_SIZE = 200  # OpenAlex maximum per-page


class OpenAlexCollector(BaseCollector):
    def __init__(self) -> None:
        headers: dict[str, str] = {}
        params: dict[str, str] = {}
        if settings.openalex_email:
            params["mailto"] = settings.openalex_email
        if settings.openalex_api_key:
            headers["Authorization"] = f"Bearer {settings.openalex_api_key}"
        self._default_params = params
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
        """Yield raw OpenAlex Work dicts up to max_results."""
        yielded = 0
        cursor = "*"

        filter_parts: list[str] = [f'title_and_abstract.search:{keyword}']
        # Require references metadata — improves citation network density and
        # filters out papers OA hasn't fully ingested. See decision 4 in
        # WORK_PROGRESS.md 2026-05-16.
        filter_parts.append("has_references:true")
        if year_start and year_end:
            filter_parts.append(f"publication_year:{year_start}-{year_end}")
        elif year_start:
            filter_parts.append(f"publication_year:>{year_start - 1}")
        elif year_end:
            filter_parts.append(f"publication_year:<{year_end + 1}")

        while yielded < max_results:
            batch_size = min(_PAGE_SIZE, max_results - yielded)
            data = self._fetch_page(
                filter_str=",".join(filter_parts),
                per_page=batch_size,
                cursor=cursor,
            )
            results = data.get("results", [])
            if not results:
                break

            for item in results:
                if yielded >= max_results:
                    return
                yield item
                yielded += 1

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break

        logger.info("OpenAlex collected %d papers for keyword=%r", yielded, keyword)

    def get_paper(self, source_id: str) -> dict | None:
        """Fetch a single Work by OpenAlex ID."""
        try:
            resp = self._client.get(f"/works/{source_id}", params=self._default_params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("OpenAlex get_paper failed for %s: %s", source_id, exc)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _fetch_page(self, filter_str: str, per_page: int, cursor: str) -> dict:
        params = {
            **self._default_params,
            "filter": filter_str,
            "per-page": per_page,
            "cursor": cursor,
            "select": (
                "id,doi,title,abstract_inverted_index,publication_year,publication_date,"
                "primary_location,open_access,authorships,cited_by_count,referenced_works_count,"
                "referenced_works,concepts,keywords,type,ids,language"
            ),
        }
        resp = self._client.get("/works", params=params)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenAlexCollector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
