import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GraphType(str, enum.Enum):
    PAPER = "paper"
    AUTHOR = "author"
    KEYWORD = "keyword"


class GraphResult(Base):
    """Metadata record for a completed graph analysis.

    Paper, author, and keyword graphs are always separate records.
    Analysis data (centrality, cluster) lives in sibling tables.
    Display metadata lives in the source entity tables (Paper, Author, Keyword).
    """

    __tablename__ = "graph_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    graph_type: Mapped[GraphType] = mapped_column(
        String(20), nullable=False, index=True
    )

    node_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    cluster_count: Mapped[int] = mapped_column(Integer, default=0)

    # Algorithm parameters used
    build_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Summary stats
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Foreign key to the entity — only one will be set depending on graph_type
    paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id", ondelete="SET NULL"), nullable=True
    )
    keyword_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="SET NULL"), nullable=True
    )

    # Derived analytical properties (not display metadata)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    # citation | co_citation | bibliographic_coupling | co_authorship | co_occurrence
    edge_type: Mapped[str | None] = mapped_column(String(50), nullable=True)


class ClusterResult(Base):
    """Cluster assignment for a graph node."""

    __tablename__ = "cluster_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    algorithm: Mapped[str | None] = mapped_column(String(50), nullable=True)  # louvain | leiden


class CentralityResult(Base):
    """Per-node centrality scores. Raw metric values only — grouping into
    meaning categories (influence / hub / bridge / access) is done at query time.
    """

    __tablename__ = "centrality_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Influence
    pagerank: Mapped[float | None] = mapped_column(Float, nullable=True)
    eigenvector: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Hub
    degree: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weighted_degree: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Bridge
    betweenness: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Access
    closeness: Mapped[float | None] = mapped_column(Float, nullable=True)
