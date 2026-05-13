"""add NTIS overlay tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ntis_institutions (no FK deps — created first)
    op.create_table(
        "ntis_institutions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ntis_inst_id", sa.String(100), nullable=True, unique=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("inst_type", sa.String(50), nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("properties", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_ntis_institutions_ntis_inst_id", "ntis_institutions", ["ntis_inst_id"])
    op.create_index("ix_ntis_institutions_name", "ntis_institutions", ["name"])

    # ntis_projects
    op.create_table(
        "ntis_projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ntis_project_id", sa.String(100), nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("govt_dept", sa.String(200), nullable=True),
        sa.Column("research_agency", sa.String(200), nullable=True),
        sa.Column("performing_org", sa.String(200), nullable=True),
        sa.Column("total_budget", sa.BigInteger, nullable=True),
        sa.Column("start_year", sa.Integer, nullable=True),
        sa.Column("end_year", sa.Integer, nullable=True),
        sa.Column("status", sa.String(10), nullable=True),
        sa.Column("keywords", JSONB, nullable=True),
        sa.Column("researchers", JSONB, nullable=True),
        sa.Column("raw_payload", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_ntis_projects_job_id", "ntis_projects", ["job_id"])
    op.create_index("ix_ntis_projects_ntis_project_id", "ntis_projects", ["ntis_project_id"])

    # comparative_results
    op.create_table(
        "comparative_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ntis_project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ntis_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "matched_paper_id",
            UUID(as_uuid=True),
            sa.ForeignKey("papers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "matched_author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("match_type", sa.String(50), nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("match_details", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_comparative_results_job_id", "comparative_results", ["job_id"])
    op.create_index("ix_comparative_results_ntis_project_id", "comparative_results", ["ntis_project_id"])
    op.create_index("ix_comparative_results_matched_paper_id", "comparative_results", ["matched_paper_id"])
    op.create_index("ix_comparative_results_matched_author_id", "comparative_results", ["matched_author_id"])


def downgrade() -> None:
    op.drop_table("comparative_results")
    op.drop_table("ntis_projects")
    op.drop_table("ntis_institutions")
