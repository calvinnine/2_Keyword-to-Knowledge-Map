"""Fix paper doi unique constraint: global → per-job.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-13

The original schema had a global UNIQUE constraint on papers.doi,
which prevents the same paper from being collected in multiple jobs.
This migration drops that constraint and replaces it with a composite
UNIQUE (doi, job_id), so each job can independently collect any paper.
The partial unique index on title_normalized (for DOI-less papers) is
similarly scoped to (title_normalized, job_id).
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old global unique constraint on doi
    op.drop_constraint("papers_doi_key", "papers", type_="unique")

    # Drop old partial unique index on title_normalized WHERE doi IS NULL
    op.drop_index("ix_papers_title_normalized_no_doi", table_name="papers", if_exists=True)

    # Create composite unique constraint (doi, job_id) — partial: only when doi IS NOT NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_papers_doi_job "
        "ON papers (doi, job_id) WHERE doi IS NOT NULL"
    )

    # Create composite unique index (title_normalized, job_id) WHERE doi IS NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_papers_title_job "
        "ON papers (title_normalized, job_id) WHERE doi IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_papers_doi_job")
    op.execute("DROP INDEX IF EXISTS uq_papers_title_job")

    # Restore original constraints (may fail if duplicates exist)
    op.create_unique_constraint("papers_doi_key", "papers", ["doi"])
    op.execute(
        "CREATE UNIQUE INDEX ix_papers_title_normalized_no_doi "
        "ON papers (title_normalized) WHERE doi IS NULL"
    )
