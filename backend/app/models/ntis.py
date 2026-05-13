"""NTIS (국가과학기술정보서비스) overlay models.

Three tables:
  ntis_projects        — R&D 과제 (research projects from NTIS API)
  ntis_institutions    — 수행기관 (de-duplicated performing organisations)
  comparative_results  — links NTIS projects to K2KM papers / authors
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NtisProject(Base):
    """NTIS R&D 과제 (research project record)."""

    __tablename__ = "ntis_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # NTIS native identifiers
    ntis_project_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Project metadata
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Funding chain
    govt_dept: Mapped[str | None] = mapped_column(String(200), nullable=True)       # 부처명
    research_agency: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 전문기관명
    performing_org: Mapped[str | None] = mapped_column(String(200), nullable=True)   # 수행기관명

    # Budget and period
    total_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)      # 총 연구비 (원)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status: Y=진행중, N=완료
    status: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Structured sub-data
    keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True)    # list[str]
    researchers: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list[{name, role, institution}]

    # Full raw payload for forward compatibility
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NtisInstitution(Base):
    """De-duplicated performing organisation referenced from NTIS projects."""

    __tablename__ = "ntis_institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ntis_inst_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    inst_type: Mapped[str | None] = mapped_column(String(50), nullable=True)   # 대학/기업/출연연/정부/병원/기타
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)   # 지역 (시/도)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MatchType(str, enum.Enum):
    KEYWORD_OVERLAP = "keyword_overlap"
    AUTHOR_NAME = "author_name"
    INSTITUTION_NAME = "institution_name"


class ComparativeResult(Base):
    """Links an NTIS project to papers / authors found in the K2KM graph."""

    __tablename__ = "comparative_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ntis_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ntis_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Matched K2KM entity (at most one of these is non-NULL per row)
    matched_paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matched_author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    match_type: Mapped[str] = mapped_column(String(50), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
