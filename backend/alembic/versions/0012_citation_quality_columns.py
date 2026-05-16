"""add citation quality columns: source, influential, journal/preprint breakdown

Background: extending the citation-enrichment policy beyond a single count.
- `citation_source`: 's2' | 'openalex' (which source produced the headline number)
- `influential_citation_count`: S2's AI-classified "core" citations
- `citation_by_journal` / `citation_by_preprint`: breakdown of citing papers' venue types
See WORK_PROGRESS.md 2026-05-16 for rationale.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column("influential_citation_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "papers",
        sa.Column("citation_by_journal", sa.Integer(), nullable=True),
    )
    op.add_column(
        "papers",
        sa.Column("citation_by_preprint", sa.Integer(), nullable=True),
    )
    op.add_column(
        "papers",
        sa.Column("citation_source", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("papers", "citation_source")
    op.drop_column("papers", "citation_by_preprint")
    op.drop_column("papers", "citation_by_journal")
    op.drop_column("papers", "influential_citation_count")
