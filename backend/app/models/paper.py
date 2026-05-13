import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Paper(Base):
    """Canonical paper entity after deduplication and normalization.

    DOI is the primary deduplication key. Title-normalization is the fallback.
    """

    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Deduplication keys
    doi: Mapped[str | None] = mapped_column(String(500), nullable=True, unique=True, index=True)
    # Normalized title fingerprint for fallback dedup
    title_normalized: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)

    # Display metadata
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    publication_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Venue
    venue_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    venue_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # journal / conference / preprint / other
    venue_issn: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # linking ISSN from OpenAlex

    # WoS classification: SCIE / SSCI / AHCI / ESCI — populated by ISSN lookup against wos_journals table
    sci_classification: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    # Citation counts from sources
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    reference_count: Mapped[int] = mapped_column(Integer, default=0)

    # External identifiers
    openalex_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    semantic_scholar_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    pubmed_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Open access info
    is_open_access: Mapped[bool | None] = mapped_column(nullable=True)

    # Language
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Fields of study from source
    fields_of_study: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Which job first ingested this paper
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PaperSource(Base):
    """Links a canonical Paper to its per-source raw record."""

    __tablename__ = "paper_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # openalex | semantic_scholar
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_payload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_payloads.id", ondelete="SET NULL"),
        nullable=True,
    )


class PaperAuthor(Base):
    __tablename__ = "paper_authors"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="CASCADE"),
        primary_key=True,
    )
    author_position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-indexed


class PaperKeyword(Base):
    __tablename__ = "paper_keywords"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    keyword_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keywords.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # openalex | semantic_scholar | mesh


class Citation(Base):
    """Directed citation edge: citing_paper cites cited_paper."""

    __tablename__ = "citations"

    citing_paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cited_paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Source that provided this citation edge
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
