"""widen author_affiliations.raw_affiliation to TEXT

OpenAlex occasionally returns very long raw_affiliation strings (multi-line
institutional affiliations with full addresses concatenated). The 1000-char
limit caused processing to fail on edge cases.

Switching to TEXT removes the limit; storage cost is negligible since most
rows remain short.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "author_affiliations",
        "raw_affiliation",
        existing_type=sa.String(length=1000),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Truncate any over-long values before re-narrowing
    op.execute("""
        UPDATE author_affiliations
        SET raw_affiliation = LEFT(raw_affiliation, 1000)
        WHERE LENGTH(raw_affiliation) > 1000
    """)
    op.alter_column(
        "author_affiliations",
        "raw_affiliation",
        existing_type=sa.Text(),
        type_=sa.String(length=1000),
        existing_nullable=True,
    )
