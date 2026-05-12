import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # External identifiers
    openalex_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    semantic_scholar_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    orcid: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Aggregated stats (updated during processing)
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Derived from affiliation majority vote across all papers — never inferred from name/ethnicity.
    # Populated by processing pipeline; null until at least one affiliation is resolved.
    primary_country_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    primary_country_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuthorAffiliation(Base):
    """Affiliation of an author as recorded on a specific paper.

    Country is derived from affiliation metadata only — never from nationality.
    """

    __tablename__ = "author_affiliations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Paper context — same author may have different affiliations per paper
    paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Raw affiliation string from source
    raw_affiliation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # ISO 3166-1 alpha-2
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    country_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
