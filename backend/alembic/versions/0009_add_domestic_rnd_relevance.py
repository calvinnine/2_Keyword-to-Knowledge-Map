"""Add domestic_rnd_relevance to author_metrics.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "author_metrics",
        sa.Column("domestic_rnd_relevance", sa.Float(), nullable=True),
    )
    op.create_index(
        "ix_author_metrics_domestic_rnd_relevance",
        "author_metrics",
        ["domestic_rnd_relevance"],
    )


def downgrade() -> None:
    op.drop_index("ix_author_metrics_domestic_rnd_relevance", table_name="author_metrics")
    op.drop_column("author_metrics", "domestic_rnd_relevance")
