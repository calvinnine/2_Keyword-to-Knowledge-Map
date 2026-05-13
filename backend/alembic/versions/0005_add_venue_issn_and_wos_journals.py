"""add venue_issn to papers and create wos_journals table

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add venue_issn column to papers
    op.add_column(
        "papers",
        sa.Column("venue_issn", sa.String(20), nullable=True),
    )
    op.create_index("ix_papers_venue_issn", "papers", ["venue_issn"])
    op.create_index("ix_papers_sci_classification", "papers", ["sci_classification"])

    # Create wos_journals table
    op.create_table(
        "wos_journals",
        sa.Column("issn_l", sa.String(20), primary_key=True),
        sa.Column("wos_index", sa.String(10), primary_key=True),
        sa.Column("journal_title", sa.String(500), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("wos_journals")
    op.drop_index("ix_papers_sci_classification", table_name="papers")
    op.drop_index("ix_papers_venue_issn", table_name="papers")
    op.drop_column("papers", "venue_issn")
