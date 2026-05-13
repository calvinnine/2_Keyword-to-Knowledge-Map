"""add publication_scope to analysis_jobs

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("publication_scope", sa.String(20), nullable=False, server_default="all"),
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "publication_scope")
