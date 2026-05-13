"""Paper Evidence Weight (PEW) — MVP implementation.

PEW = 0.35 × Topical Relevance
    + 0.30 × Citation Impact
    + 0.20 × Network Centrality
    + 0.10 × Recency
    + 0.05 × Reliability

All component scores are normalised to [0, 1].
"""

import logging
import math
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph import GraphResult, GraphNode, CentralityResult, GraphType
from app.models.paper import Paper
from app.models.metrics import PaperMetrics

logger = logging.getLogger(__name__)

_CURRENT_YEAR = date.today().year

# PEW weights (sum = 1.0)
_W_TOPICAL = 0.35
_W_CITATION = 0.30
_W_CENTRALITY = 0.20
_W_RECENCY = 0.10
_W_RELIABILITY = 0.05


def compute_paper_metrics(
    db: Session,
    job_id: uuid.UUID,
    paper_graph: GraphResult,
) -> dict[uuid.UUID, float]:
    """Compute PaperMetrics for every paper in a job corpus.

    Returns mapping {paper_id → evidence_weight} for downstream use.
    Must be called after compute_centrality() on the paper graph.
    """
    if paper_graph.graph_type != GraphType.PAPER:
        raise ValueError("Expected a PAPER graph result")

    # Load papers for this job
    papers = db.execute(
        select(Paper).where(Paper.job_id == job_id)
    ).scalars().all()
    if not papers:
        return {}

    paper_map = {p.id: p for p in papers}

    # Load paper-graph nodes (paper_id → node_id)
    nodes = db.execute(
        select(GraphNode).where(
            GraphNode.graph_id == paper_graph.id,
            GraphNode.paper_id.in_(list(paper_map.keys())),
        )
    ).scalars().all()
    paper_to_node: dict[uuid.UUID, uuid.UUID] = {n.paper_id: n.id for n in nodes if n.paper_id}

    # Load centrality scores keyed by node_id
    centrality_rows = db.execute(
        select(CentralityResult).where(CentralityResult.graph_id == paper_graph.id)
    ).scalars().all()
    centrality: dict[uuid.UUID, CentralityResult] = {r.node_id: r for r in centrality_rows}

    # Cluster id per node_id (for topical relevance)
    cluster_map: dict[uuid.UUID, int | None] = {n.id: n.cluster_id for n in nodes}
    # Main clusters = top-2 by size
    cluster_sizes: dict[int, int] = {}
    for n in nodes:
        if n.cluster_id is not None:
            cluster_sizes[n.cluster_id] = cluster_sizes.get(n.cluster_id, 0) + 1
    top_clusters: set[int] = set(
        sorted(cluster_sizes, key=lambda c: cluster_sizes[c], reverse=True)[:2]
    )

    # --- Normalise citation counts to [0, 1] percentile within corpus ---
    citation_counts = [p.citation_count or 0 for p in papers]
    citation_counts_sorted = sorted(citation_counts)
    n_papers = len(citation_counts_sorted)

    def citation_percentile(count: int) -> float:
        if n_papers <= 1:
            return 0.5
        rank = sum(1 for c in citation_counts_sorted if c <= count)
        return rank / n_papers

    # --- Normalise PageRank to [0, 1] ---
    pageranks = {r.node_id: (r.pagerank or 0.0) for r in centrality_rows}
    pr_max = max(pageranks.values(), default=1e-9)

    pew_map: dict[uuid.UUID, float] = {}
    rows_to_insert: list[PaperMetrics] = []

    for paper in papers:
        node_id = paper_to_node.get(paper.id)
        cr = centrality.get(node_id) if node_id else None

        # 1. Topical Relevance
        #    Base 0.7 (all papers matched the keyword search)
        #    Bonus for main clusters (+0.2) or title keyword hint (+0.1)
        topical = 0.70
        if node_id and cluster_map.get(node_id) in top_clusters:
            topical += 0.20
        topical = min(topical, 1.0)

        # 2. Citation Impact — percentile within corpus
        citation_impact = citation_percentile(paper.citation_count or 0)

        # 3. Network Centrality — normalised PageRank
        pr = (cr.pagerank or 0.0) if cr else 0.0
        network_centrality = min(pr / pr_max, 1.0) if pr_max > 0 else 0.0

        # 4. Recency
        year = paper.publication_year or (_CURRENT_YEAR - 10)
        age = _CURRENT_YEAR - year
        if age <= 3:
            recency = 1.0
        elif age <= 7:
            recency = 0.75
        elif age <= 12:
            recency = 0.50
        else:
            recency = max(0.20, 1.0 - age * 0.03)

        # 5. Reliability
        reliability = 0.0
        if paper.sci_classification in ("SCIE", "SSCI", "AHCI", "ESCI"):
            reliability += 0.40
        if paper.doi:
            reliability += 0.25
        if paper.abstract:
            reliability += 0.20
        if paper.is_open_access:
            reliability += 0.10
        if paper.title:
            reliability += 0.05
        reliability = min(reliability, 1.0)

        # PEW composite
        pew = (
            _W_TOPICAL * topical
            + _W_CITATION * citation_impact
            + _W_CENTRALITY * network_centrality
            + _W_RECENCY * recency
            + _W_RELIABILITY * reliability
        )

        pew_map[paper.id] = pew
        rows_to_insert.append(PaperMetrics(
            id=uuid.uuid4(),
            paper_id=paper.id,
            job_id=job_id,
            topical_relevance=round(topical, 4),
            citation_impact=round(citation_impact, 4),
            network_centrality=round(network_centrality, 4),
            recency=round(recency, 4),
            reliability=round(reliability, 4),
            evidence_weight=round(pew, 4),
        ))

    db.add_all(rows_to_insert)
    logger.info(
        "PaperMetrics computed for job %s: %d papers, avg PEW=%.3f",
        job_id, len(rows_to_insert),
        sum(pew_map.values()) / max(len(pew_map), 1),
    )
    return pew_map
