"""make paper.citation_count nullable

Reason: switching authoritative citation source from OpenAlex to Semantic
Scholar. OpenAlex was observed to ship citation counts contaminated by
cross-work merge errors (counts spanning years before the publication date).
S2 verifies citation counts paper-by-paper. When S2 can't verify a paper
(no DOI / not indexed), we now store NULL instead of an unreliable integer.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "papers",
        "citation_count",
        existing_type=sa.Integer(),
        nullable=True,
        existing_server_default=sa.text("0"),
        server_default=None,
    )


def downgrade() -> None:
    # Backfill NULLs with 0 before re-imposing NOT NULL
    op.execute("UPDATE papers SET citation_count = 0 WHERE citation_count IS NULL")
    op.alter_column(
        "papers",
        "citation_count",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )
