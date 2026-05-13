"""extend publication_scope column length for multi-select

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "analysis_jobs",
        "publication_scope",
        existing_type=sa.String(20),
        type_=sa.String(100),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "analysis_jobs",
        "publication_scope",
        existing_type=sa.String(100),
        type_=sa.String(20),
        existing_nullable=False,
    )
