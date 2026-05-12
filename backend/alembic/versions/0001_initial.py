"""Initial schema for K2KM MVP Phase 1-3.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-12

Creates: analysis_jobs, raw_payloads, institutions, authors, author_affiliations,
keywords, papers, paper_sources, paper_authors, paper_keywords, citations,
graph_results, graph_nodes, graph_edges, cluster_results, centrality_results.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("keyword", sa.String(500), nullable=False),
        sa.Column("status", sa.Enum(
            "pending", "collecting", "collected", "processing", "processed",
            "analyzing", "completed", "failed", "cancelled",
            name="jobstatus"
        ), nullable=False),
        sa.Column("max_papers", sa.Integer(), nullable=False, server_default="20000"),
        sa.Column("year_start", sa.Integer()),
        sa.Column("year_end", sa.Integer()),
        sa.Column("publication_types", postgresql.JSONB()),
        sa.Column("papers_collected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("papers_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("params", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_analysis_jobs_keyword", "analysis_jobs", ["keyword"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])

    op.create_table(
        "raw_payloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_raw_payloads_job_id", "raw_payloads", ["job_id"])
    op.create_index("ix_raw_payloads_source", "raw_payloads", ["source"])
    op.create_index("ix_raw_payloads_source_id", "raw_payloads", ["source_id"])

    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("country_code", sa.String(10)),
        sa.Column("country_name", sa.String(200)),
        sa.Column("openalex_id", sa.String(100), unique=True),
        sa.Column("ror_id", sa.String(100)),
        sa.Column("extra", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_institutions_country_code", "institutions", ["country_code"])
    op.create_index("ix_institutions_openalex_id", "institutions", ["openalex_id"])
    op.create_index("ix_institutions_ror_id", "institutions", ["ror_id"])

    op.create_table(
        "authors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("openalex_id", sa.String(100), unique=True),
        sa.Column("semantic_scholar_id", sa.String(100)),
        sa.Column("orcid", sa.String(100)),
        sa.Column("paper_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_authors_name", "authors", ["name"])
    op.create_index("ix_authors_openalex_id", "authors", ["openalex_id"])
    op.create_index("ix_authors_semantic_scholar_id", "authors", ["semantic_scholar_id"])
    op.create_index("ix_authors_orcid", "authors", ["orcid"])

    op.create_table(
        "keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("normalized", sa.String(500), nullable=False, unique=True),
        sa.Column("display", sa.String(500), nullable=False),
        sa.Column("paper_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_keywords_normalized", "keywords", ["normalized"])

    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("doi", sa.String(500), unique=True),
        sa.Column("title_normalized", sa.String(1000)),
        sa.Column("title", sa.Text()),
        sa.Column("abstract", sa.Text()),
        sa.Column("publication_year", sa.Integer()),
        sa.Column("publication_date", sa.String(20)),
        sa.Column("venue_name", sa.String(500)),
        sa.Column("venue_type", sa.String(50)),
        sa.Column("sci_classification", sa.String(50)),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reference_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("openalex_id", sa.String(100)),
        sa.Column("semantic_scholar_id", sa.String(100)),
        sa.Column("pubmed_id", sa.String(100)),
        sa.Column("arxiv_id", sa.String(100)),
        sa.Column("is_open_access", sa.Boolean()),
        sa.Column("language", sa.String(10)),
        sa.Column("fields_of_study", postgresql.JSONB()),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_jobs.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_papers_doi", "papers", ["doi"])
    op.create_index("ix_papers_title_normalized", "papers", ["title_normalized"])
    op.create_index("ix_papers_publication_year", "papers", ["publication_year"])
    op.create_index("ix_papers_openalex_id", "papers", ["openalex_id"])
    op.create_index("ix_papers_semantic_scholar_id", "papers", ["semantic_scholar_id"])
    op.create_index("ix_papers_job_id", "papers", ["job_id"])

    op.create_table(
        "paper_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("raw_payload_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("raw_payloads.id", ondelete="SET NULL")),
    )
    op.create_index("ix_paper_sources_paper_id", "paper_sources", ["paper_id"])
    op.create_index("ix_paper_sources_source_id", "paper_sources", ["source_id"])

    op.create_table(
        "paper_authors",
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("author_position", sa.Integer()),
    )

    op.create_table(
        "paper_keywords",
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("keyword_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source", sa.String(50)),
    )

    op.create_table(
        "citations",
        sa.Column("citing_paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cited_paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source", sa.String(50)),
    )

    op.create_table(
        "author_affiliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("institutions.id", ondelete="SET NULL")),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE")),
        sa.Column("raw_affiliation", sa.String(1000)),
        sa.Column("country_code", sa.String(10)),
        sa.Column("country_name", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_author_affiliations_author_id", "author_affiliations", ["author_id"])
    op.create_index("ix_author_affiliations_paper_id", "author_affiliations", ["paper_id"])
    op.create_index("ix_author_affiliations_country_code", "author_affiliations", ["country_code"])

    op.create_table(
        "graph_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("graph_type", sa.String(20), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edge_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cluster_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("build_params", postgresql.JSONB()),
        sa.Column("stats", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_graph_results_job_id", "graph_results", ["job_id"])
    op.create_index("ix_graph_results_graph_type", "graph_results", ["graph_type"])

    op.create_table(
        "graph_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("graph_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="SET NULL")),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("authors.id", ondelete="SET NULL")),
        sa.Column("keyword_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("keywords.id", ondelete="SET NULL")),
        sa.Column("cluster_id", sa.Integer()),
        sa.Column("properties", postgresql.JSONB()),
    )
    op.create_index("ix_graph_nodes_graph_id", "graph_nodes", ["graph_id"])
    op.create_index("ix_graph_nodes_cluster_id", "graph_nodes", ["cluster_id"])

    op.create_table(
        "graph_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("graph_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("edge_type", sa.String(50)),
    )
    op.create_index("ix_graph_edges_graph_id", "graph_edges", ["graph_id"])

    op.create_table(
        "cluster_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("graph_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("algorithm", sa.String(50)),
    )
    op.create_index("ix_cluster_results_graph_id", "cluster_results", ["graph_id"])
    op.create_index("ix_cluster_results_node_id", "cluster_results", ["node_id"])
    op.create_index("ix_cluster_results_cluster_id", "cluster_results", ["cluster_id"])

    op.create_table(
        "centrality_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("graph_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pagerank", sa.Float()),
        sa.Column("eigenvector", sa.Float()),
        sa.Column("degree", sa.Integer()),
        sa.Column("weighted_degree", sa.Float()),
        sa.Column("betweenness", sa.Float()),
        sa.Column("closeness", sa.Float()),
    )
    op.create_index("ix_centrality_results_graph_id", "centrality_results", ["graph_id"])
    op.create_index("ix_centrality_results_node_id", "centrality_results", ["node_id"])


def downgrade() -> None:
    op.drop_table("centrality_results")
    op.drop_table("cluster_results")
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("graph_results")
    op.drop_table("author_affiliations")
    op.drop_table("citations")
    op.drop_table("paper_keywords")
    op.drop_table("paper_authors")
    op.drop_table("paper_sources")
    op.drop_table("papers")
    op.drop_table("keywords")
    op.drop_table("authors")
    op.drop_table("institutions")
    op.drop_table("raw_payloads")
    op.drop_table("analysis_jobs")
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=True)
