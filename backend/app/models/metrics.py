"""Per-job analytical metrics for papers and authors.

PaperMetrics  — Paper Evidence Weight and component scores (scoped per job).
AuthorMetrics — Aggregated author scores, role labels, and caution flags.
"""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaperMetrics(Base):
    """Paper Evidence Weight and sub-scores for a specific job corpus.

    Scoped per (paper_id, job_id) — the same paper can have different scores
    in different jobs depending on the corpus composition.
    """

    __tablename__ = "paper_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Component scores [0, 1]
    topical_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_centrality: Mapped[float | None] = mapped_column(Float, nullable=True)
    recency: Mapped[float | None] = mapped_column(Float, nullable=True)
    reliability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Final composite score [0, 1]
    evidence_weight: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)


class AuthorMetrics(Base):
    """Aggregated author scores and role labels for a specific job corpus.

    Scoped per (author_id, job_id).
    """

    __tablename__ = "author_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Paper production
    related_paper_count: Mapped[int] = mapped_column(Integer, default=0)
    productivity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Impact components [0, 1]
    author_impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    structural_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Composite [0, 1]
    global_scholarly_impact: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    # Quality guard
    low_impact_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Role labels — list of role label strings, e.g. ["Core Influencer", "Bridge Researcher"]
    role_labels: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Caution flags — list of flag code strings, e.g. ["OLD_IMPACT_ONLY"]
    caution_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
