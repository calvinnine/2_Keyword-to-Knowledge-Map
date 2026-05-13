"""Add x_pos, y_pos to graph_nodes for pre-computed layout

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("graph_nodes", sa.Column("x_pos", sa.Float(), nullable=True))
    op.add_column("graph_nodes", sa.Column("y_pos", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("graph_nodes", "y_pos")
    op.drop_column("graph_nodes", "x_pos")
