"""Add paper_metrics and author_metrics tables (Paper Evidence Weight + role labels)

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID(as_uuid=True),
                  sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topical_relevance", sa.Float(), nullable=True),
        sa.Column("citation_impact", sa.Float(), nullable=True),
        sa.Column("network_centrality", sa.Float(), nullable=True),
        sa.Column("recency", sa.Float(), nullable=True),
        sa.Column("reliability", sa.Float(), nullable=True),
        sa.Column("evidence_weight", sa.Float(), nullable=True),
    )
    op.create_index("ix_paper_metrics_paper_id", "paper_metrics", ["paper_id"])
    op.create_index("ix_paper_metrics_job_id", "paper_metrics", ["job_id"])
    op.create_index("ix_paper_metrics_evidence_weight", "paper_metrics", ["evidence_weight"])

    op.create_table(
        "author_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", UUID(as_uuid=True),
                  sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID(as_uuid=True),
                  sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_paper_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("productivity_score", sa.Float(), nullable=True),
        sa.Column("author_impact_score", sa.Float(), nullable=True),
        sa.Column("structural_score", sa.Float(), nullable=True),
        sa.Column("momentum_score", sa.Float(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("global_scholarly_impact", sa.Float(), nullable=True),
        sa.Column("low_impact_ratio", sa.Float(), nullable=True),
        sa.Column("role_labels", JSONB(), nullable=True),
        sa.Column("caution_flags", JSONB(), nullable=True),
    )
    op.create_index("ix_author_metrics_author_id", "author_metrics", ["author_id"])
    op.create_index("ix_author_metrics_job_id", "author_metrics", ["job_id"])
    op.create_index("ix_author_metrics_global_scholarly_impact",
                    "author_metrics", ["global_scholarly_impact"])


def downgrade() -> None:
    op.drop_table("author_metrics")
    op.drop_table("paper_metrics")
