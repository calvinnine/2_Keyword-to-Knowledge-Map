"""NTIS ingestion service.

Converts parsed NTIS project/paper dicts (from ntis.py collectors) into
NtisProject / NtisInstitution rows.

Field mapping (과제검색 API → 우리 스키마):
  ProjectNumber            → ntis_project_id
  ProjectTitle_Korean      → title
  Abstract_Teaser          → abstract
  Ministry_Name            → govt_dept
  OrderAgency_Name         → research_agency  (전문기관)
  ResearchAgency_Name      → performing_org   (수행기관)
  TotalFunds               → total_budget
  ProjectPeriod_TotalStart → start_year (YYYYMMDD → year)
  ProjectPeriod_TotalEnd   → end_year
  Keyword_Korean           → keywords (콤마 분리)
  Manager_Name             → researchers[0] (책임연구자)
  Researchers_Name         → researchers[1..] (참여연구원, ;로 나열)
"""

import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ntis import NtisProject, NtisInstitution

logger = logging.getLogger(__name__)

_INST_CACHE: dict[str, uuid.UUID] = {}


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _parse_year(ymd: str | None) -> int | None:
    if not ymd:
        return None
    try:
        return int(str(ymd)[:4])
    except (ValueError, TypeError):
        return None


def _parse_keywords(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,，；;]", raw)
    return [p.strip() for p in parts if p.strip()]


def _parse_researchers(raw: dict) -> list[dict]:
    """Build researcher list from 연구책임자 + 참여연구원 fields."""
    result = []
    manager = raw.get("Manager_Name") or ""
    if manager.strip():
        result.append({"name": manager.strip(), "role": "PI", "institution": raw.get("ResearchAgency_Name") or ""})

    others_raw = raw.get("Researchers_Name") or ""
    for name in others_raw.split(";"):
        name = name.strip()
        if name and name != manager.strip():
            result.append({"name": name, "role": "Co-I", "institution": raw.get("ResearchAgency_Name") or ""})

    return result


class NtisIngestionService:
    def __init__(self, db: Session, job_id: uuid.UUID) -> None:
        self._db = db
        self._job_id = job_id
        _INST_CACHE.clear()

    def ingest_project(self, raw: dict[str, Any]) -> NtisProject | None:
        """Convert one parsed project dict to a NtisProject row.

        Returns existing row if already stored (upsert by ntis_project_id).
        Returns None if record is invalid.
        """
        ntis_id = raw.get("ProjectNumber")
        title = raw.get("ProjectTitle_Korean") or ""
        if not title.strip():
            return None

        if ntis_id:
            existing = self._db.execute(
                select(NtisProject).where(
                    NtisProject.job_id == self._job_id,
                    NtisProject.ntis_project_id == str(ntis_id),
                )
            ).scalar_one_or_none()
            if existing:
                return existing

        performing_org = raw.get("ResearchAgency_Name") or None
        if performing_org:
            self._upsert_institution(performing_org, raw)

        budget = _parse_budget(raw.get("TotalFunds"))

        project = NtisProject(
            id=uuid.uuid4(),
            job_id=self._job_id,
            ntis_project_id=str(ntis_id) if ntis_id else None,
            title=title.strip(),
            abstract=(raw.get("Abstract_Teaser") or raw.get("Goal_Teaser") or "").strip() or None,
            govt_dept=raw.get("Ministry_Name"),
            research_agency=raw.get("OrderAgency_Name"),
            performing_org=performing_org,
            total_budget=budget,
            start_year=_parse_year(raw.get("ProjectPeriod_TotalStart")),
            end_year=_parse_year(raw.get("ProjectPeriod_TotalEnd")),
            status=None,  # 과제검색 API에 상태 필드 없음
            keywords=_parse_keywords(raw.get("Keyword_Korean")),
            researchers=_parse_researchers(raw),
            raw_payload=raw,
        )
        self._db.add(project)
        return project

    def _upsert_institution(self, name: str, raw: dict) -> uuid.UUID:
        key = _norm_name(name)
        if key in _INST_CACHE:
            return _INST_CACHE[key]

        existing = self._db.execute(
            select(NtisInstitution).where(NtisInstitution.name == name)
        ).scalar_one_or_none()

        if existing:
            _INST_CACHE[key] = existing.id
            return existing.id

        inst = NtisInstitution(
            id=uuid.uuid4(),
            ntis_inst_id=None,
            name=name,
            inst_type=_infer_inst_type(name),
            location=None,
        )
        self._db.add(inst)
        self._db.flush()
        _INST_CACHE[key] = inst.id
        return inst.id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_budget(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(str(raw).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


_UNIV_KEYWORDS = ("대학교", "대학", "university", "college")
_GOVT_KEYWORDS = ("부처", "청", "처", "ministry", "agency")
_COMPANY_KEYWORDS = ("주식회사", "(주)", "(유)", "co.,", "corp.", "inc.", "ltd.")
_RES_KEYWORDS = ("연구원", "연구소", "연구센터", "research", "과학기술원", "kaist", "postech", "gist", "dgist", "unist")
_HOSP_KEYWORDS = ("병원", "의료원", "hospital", "medical center")


def _infer_inst_type(name: str) -> str:
    n = name.lower()
    if any(k in n for k in _UNIV_KEYWORDS):
        return "university"
    if any(k in n for k in _HOSP_KEYWORDS):
        return "hospital"
    if any(k in n for k in _RES_KEYWORDS):
        return "research_institute"
    if any(k in n for k in _COMPANY_KEYWORDS):
        return "company"
    if any(k in n for k in _GOVT_KEYWORDS):
        return "government"
    return "other"
