"""NTIS (국가과학기술지식정보서비스) collector.

기술문서 기반 실제 스펙:
  과제검색: GET https://www.ntis.go.kr/rndopen/openApi/public_project
  성과검색: GET https://www.ntis.go.kr/rndopen/openApi/public_result  (collection=rpaper)
  연관콘텐츠: GET https://www.ntis.go.kr/rndopen/openApi/ConnectionContent

인증: apprvKey 쿼리 파라미터
응답 포맷: XML (과제/성과), JSON (연관콘텐츠)
페이지네이션: startPosition + displayCnt (최대 100)

API 키가 없으면 빈 제너레이터를 반환하여 파이프라인을 중단시키지 않는다.
"""

import logging
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.ntis.go.kr"
_PROJECT_PATH = "/rndopen/openApi/public_project"
_RESULT_PATH = "/rndopen/openApi/public_result"
_RELATED_PATH = "/rndopen/openApi/ConnectionContent"
_PAGE_SIZE = 100  # NTIS API max per page
_PARALLEL_WORKERS = 4  # concurrent page fetches; NTIS handles modest concurrency well


class NtisApiError(RuntimeError):
    """Raised when NTIS returns an `<error>` XML body (HTTP 200)."""


class NtisCollector:
    """Collect R&D project and paper outcome records from the NTIS Open API."""

    def __init__(self) -> None:
        self._api_key = settings.ntis_api_key
        # `limits` enables connection pool reuse across parallel page fetches.
        self._client = httpx.Client(
            base_url=_BASE_URL,
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=_PARALLEL_WORKERS * 2,
                max_keepalive_connections=_PARALLEL_WORKERS,
            ),
        )

    # ------------------------------------------------------------------
    # Public: 과제 검색
    # ------------------------------------------------------------------

    def search_projects(
        self,
        keyword: str,
        max_results: int,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> Generator[dict, None, None]:
        """Yield parsed project dicts from 과제검색 API.

        Strategy: fetch page 1 synchronously to learn TOTALHITS, then fetch the
        remaining pages in parallel via a thread pool. NTIS handles 4-way
        concurrency comfortably, cutting wall-clock time roughly 4×.
        """
        if not self._api_key:
            logger.info("NTIS_API_KEY not set; skipping project collection")
            return

        add_query_parts = []
        if year_start and year_end:
            add_query_parts.append(f"PY={year_start}/MORE,{year_end}/UNDER")
        elif year_start:
            add_query_parts.append(f"PY={year_start}/MORE")
        elif year_end:
            add_query_parts.append(f"PY={year_end}/UNDER")
        add_query = "&".join(add_query_parts)

        def build_params(start_pos: int, batch: int) -> dict:
            return {
                "apprvKey": self._api_key,
                "collection": "project",
                "SRWR": keyword,
                "searchFd": "BI",
                "addQuery": add_query,
                "startPosition": start_pos,
                "displayCnt": batch,
                "searchRnkn": "DATE/DESC",
            }

        yield from self._paginated_search(
            path=_PROJECT_PATH,
            build_params=build_params,
            parser=_parse_project_hit,
            max_results=max_results,
            label="project",
            keyword=keyword,
        )

    # ------------------------------------------------------------------
    # Public: 성과(논문) 검색
    # ------------------------------------------------------------------

    def search_papers(
        self,
        keyword: str,
        max_results: int,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> Generator[dict, None, None]:
        """Yield parsed paper outcome dicts from 성과검색 API (collection=rpaper)."""
        if not self._api_key:
            logger.info("NTIS_API_KEY not set; skipping paper outcome collection")
            return

        add_query_parts = ["DBT=PAP"]
        if year_start and year_end:
            add_query_parts.append(f"PY={year_start}/MORE,{year_end}/UNDER")
        elif year_start:
            add_query_parts.append(f"PY={year_start}/MORE")
        elif year_end:
            add_query_parts.append(f"PY={year_end}/UNDER")
        add_query = "&".join(add_query_parts)

        def build_params(start_pos: int, batch: int) -> dict:
            return {
                "apprvKey": self._api_key,
                "collection": "rpaper",
                "SRWR": keyword,
                "searchFd": "BI",
                "addQuery": add_query,
                "startPosition": start_pos,
                "displayCnt": batch,
                "searchRnkn": "DATE/DESC",
            }

        yield from self._paginated_search(
            path=_RESULT_PATH,
            build_params=build_params,
            parser=_parse_paper_hit,
            max_results=max_results,
            label="paper outcome",
            keyword=keyword,
        )

    # ------------------------------------------------------------------
    # Internal: parallel pagination
    # ------------------------------------------------------------------

    def _paginated_search(
        self,
        path: str,
        build_params,
        parser,
        max_results: int,
        label: str,
        keyword: str,
    ) -> Generator[dict, None, None]:
        """Fetch page 1, then parallelise the remaining pages."""
        # --- Page 1: synchronous to learn TOTALHITS ---
        try:
            root = self._fetch_xml(path=path, params=build_params(1, min(_PAGE_SIZE, max_results)))
        except NtisApiError:
            # Permanent error (IP whitelist / bad key / quota) — let it bubble
            # up so callers can surface a useful message to the user.
            raise
        except Exception as exc:
            logger.warning("NTIS %s fetch failed at start=1: %s", label, exc)
            return

        hits = root.findall(".//RESULTSET/HIT")
        total_el = root.find(".//TOTALHITS")
        total = int(total_el.text) if total_el is not None and total_el.text else 0
        target = min(max_results, total) if total else max_results

        yielded = 0
        for hit in hits:
            if yielded >= target:
                logger.info("NTIS collected %d %ss for keyword=%r", yielded, label, keyword)
                return
            yield parser(hit)
            yielded += 1

        if yielded >= target or not hits:
            logger.info("NTIS collected %d %ss for keyword=%r", yielded, label, keyword)
            return

        # --- Remaining pages: parallel ---
        page_size = len(hits)  # respect server's actual page size
        page_starts: list[int] = []
        start = yielded + 1
        while start <= target:
            page_starts.append(start)
            start += page_size

        results: dict[int, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS) as pool:
            futures = {
                pool.submit(
                    self._fetch_page_items,
                    path,
                    build_params(sp, min(page_size, target - sp + 1)),
                    parser,
                ): sp
                for sp in page_starts
            }
            for fut in as_completed(futures):
                sp = futures[fut]
                try:
                    results[sp] = fut.result()
                except Exception as exc:
                    logger.warning("NTIS %s fetch failed at start=%d: %s", label, sp, exc)
                    results[sp] = []

        # Yield in ascending startPosition order for deterministic output
        for sp in sorted(results):
            for item in results[sp]:
                if yielded >= target:
                    break
                yield item
                yielded += 1
            if yielded >= target:
                break

        logger.info("NTIS collected %d %ss for keyword=%r", yielded, label, keyword)

    def _fetch_page_items(self, path: str, params: dict, parser) -> list[dict]:
        root = self._fetch_xml(path=path, params=params)
        return [parser(hit) for hit in root.findall(".//RESULTSET/HIT")]

    # ------------------------------------------------------------------
    # Public: 연관콘텐츠 (과제 기반 유사 과제/논문)
    # ------------------------------------------------------------------

    def get_related_projects(self, pjt_id: str, top_n: int = 10) -> list[dict]:
        """Return AI-similarity ranked project list for a given NTIS project ID."""
        if not self._api_key:
            return []
        try:
            resp = self._client.get(
                _RELATED_PATH,
                params={
                    "apprvKey": self._api_key,
                    "pjtId": pjt_id,
                    "collection": "project",
                    "topN": top_n,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("items") or []
        except Exception as exc:
            logger.warning("NTIS related projects failed for pjtId=%s: %s", pjt_id, exc)
            return []

    def get_related_papers(self, pjt_id: str, top_n: int = 10) -> list[dict]:
        """Return AI-similarity ranked paper list for a given NTIS project ID."""
        if not self._api_key:
            return []
        try:
            resp = self._client.get(
                _RELATED_PATH,
                params={
                    "apprvKey": self._api_key,
                    "pjtId": pjt_id,
                    "collection": "paper",
                    "topN": top_n,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("items") or []
        except Exception as exc:
            logger.warning("NTIS related papers failed for pjtId=%s: %s", pjt_id, exc)
            return []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "NtisCollector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_not_exception_type(NtisApiError),
        reraise=True,
    )
    def _fetch_xml(self, path: str, params: dict) -> ET.Element:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        # NTIS returns HTTP 200 with `<error>...</error>` body on auth/IP/quota
        # failures. Surface these as exceptions so retries and callers can react.
        if root.tag == "error":
            msg = (root.text or "").strip() or "NTIS API error"
            raise NtisApiError(msg)
        return root


# ---------------------------------------------------------------------------
# XML → dict parsers
# ---------------------------------------------------------------------------

def _text(el: ET.Element, tag: str) -> str | None:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_project_hit(hit: ET.Element) -> dict:
    """Extract fields from a <HIT> element of the 과제검색 API response."""
    return {
        "ProjectNumber": _text(hit, "ProjectNumber"),
        "ProjectTitle_Korean": _text(hit, "ProjectTitle/Korean"),
        "ProjectTitle_English": _text(hit, "ProjectTitle/English"),
        "Manager_Name": _text(hit, "Manager/Name"),
        "Researchers_Name": _text(hit, "Researchers/Name"),
        "Abstract_Teaser": _text(hit, "Abstract/Teaser"),
        "Goal_Teaser": _text(hit, "Goal/Teaser"),
        "Keyword_Korean": _text(hit, "Keyword/Korean"),
        "Keyword_English": _text(hit, "Keyword/English"),
        "OrderAgency_Name": _text(hit, "OrderAgency/Name"),      # 전문기관
        "ResearchAgency_Name": _text(hit, "ResearchAgency/Name"), # 수행기관
        "Ministry_Name": _text(hit, "Ministry/Name"),             # 부처명
        "BudgetProject_Name": _text(hit, "BudgetProject/Name"),   # 사업명
        "ProjectYear": _text(hit, "ProjectYear"),
        "ProjectPeriod_TotalStart": _text(hit, "ProjectPeriod/TotalStart"),
        "ProjectPeriod_TotalEnd": _text(hit, "ProjectPeriod/TotalEnd"),
        "GovernmentFunds": _text(hit, "GovernmentFunds"),
        "TotalFunds": _text(hit, "TotalFunds"),
    }


def _parse_paper_hit(hit: ET.Element) -> dict:
    """Extract fields from a <HIT> element of the 성과검색 API response."""
    return {
        "ResultID": _text(hit, "ResultID"),
        "ResultTitle": _text(hit, "ResultTitle"),
        "JournalName": _text(hit, "JournalName"),
        "IssnNumber": _text(hit, "IssnNumber"),
        "Author": _text(hit, "Author"),
        "Abstract_Teaser": _text(hit, "Abstract/Teaser"),
        "PubYear": _text(hit, "PubYear"),
        "SciType": _text(hit, "SciType"),          # 01=SCI, 02=비SCI
        "NationType": _text(hit, "NationType"),
        "ProjectID": _text(hit, "ProjectID"),       # 연결된 과제고유번호
        "ProjectTitle": _text(hit, "ProjectTitle"),
        "MinistryName": _text(hit, "MinistryName"),
        "PerformAgency": _text(hit, "PerformAgency"),
        "SourceFlag": _text(hit, "SourceFlag"),     # 원문유무 Y/N
    }
