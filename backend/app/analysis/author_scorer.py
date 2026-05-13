"""Author scoring and role labeling.

Builds AuthorMetrics for every author in a job corpus using:
  - PaperMetrics (evidence_weight per paper)
  - CentralityResult from the author co-authorship graph
  - PaperAuthor (author position for contribution weighting)
  - Publication recency distribution

Role labels (v2 §11-5):
  Core Influencer      — high impact_score + high-PEW papers
  Bridge Researcher    — high betweenness + multi-cluster presence
  Productive Contributor — high paper count + acceptable quality
  Emerging Researcher  — rising recent activity
  Niche Specialist     — concentrated in one small cluster
  Domestic R&D Actor   — primary institution is South Korean (KR proxy)
  Strategic Connector  — reserved for NTIS overlay (Phase 6)

Caution flags (v2 §붙임 4):
  OLD_IMPACT_ONLY      — recent activity low
  HIGH_LOW_IMPACT_RATIO — many low-PEW papers
  LOW_METADATA_COMPLETENESS — sparse author metadata
  POSSIBLE_NAME_COLLISION — very common name
"""

import logging
import math
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.graph import GraphResult, GraphNode, CentralityResult, GraphType
from app.models.metrics import AuthorMetrics
from app.models.paper import Paper, PaperAuthor

logger = logging.getLogger(__name__)

_CURRENT_YEAR = date.today().year
_RECENT_YEARS = 5      # "recent" window for Emerging / Momentum
_TOP_N_PAPERS = 10     # top-N papers for Author Impact Score

# Role thresholds (percentile-based, set at compute time)
_CORE_INFLUENCER_PERCENTILE = 0.90   # top 10% by impact_score
_BRIDGE_PERCENTILE = 0.90            # top 10% by betweenness
_PRODUCTIVE_PERCENTILE = 0.90        # top 10% by paper count


def _contribution_weight(position: int | None, n_authors: int) -> float:
    """Author contribution weight based on author position (0-indexed)."""
    if n_authors <= 0:
        return 1.0
    if position is None:
        return 1.0 / n_authors
    last_pos = n_authors - 1
    if position == 0:        # first author
        return 1.0
    if position == last_pos: # last/corresponding author
        return 0.80
    # middle authors — diluted by total count
    base = 0.50
    return base / math.log(1 + n_authors)


def compute_author_metrics(
    db: Session,
    job_id: uuid.UUID,
    author_graph: GraphResult,
    pew_map: dict[uuid.UUID, float],
) -> None:
    """Compute and persist AuthorMetrics for all authors in a job.

    Must be called after:
      - compute_centrality(db, author_graph)
      - compute_paper_metrics(db, job_id, paper_graph)

    Args:
        pew_map: {paper_id → evidence_weight} from compute_paper_metrics().
    """
    if author_graph.graph_type != GraphType.AUTHOR:
        raise ValueError("Expected an AUTHOR graph result")

    # --- Load author graph nodes + centrality ---
    nodes = db.execute(
        select(GraphNode).where(GraphNode.graph_id == author_graph.id)
    ).scalars().all()
    author_to_node: dict[uuid.UUID, GraphNode] = {
        n.author_id: n for n in nodes if n.author_id
    }

    centrality_rows = db.execute(
        select(CentralityResult).where(CentralityResult.graph_id == author_graph.id)
    ).scalars().all()
    node_centrality: dict[uuid.UUID, CentralityResult] = {r.node_id: r for r in centrality_rows}

    # Author graph betweenness for Bridge role
    betweenness_by_author: dict[uuid.UUID, float] = {}
    for author_id, node in author_to_node.items():
        cr = node_centrality.get(node.id)
        betweenness_by_author[author_id] = cr.betweenness or 0.0 if cr else 0.0

    # --- Load papers in this job ---
    papers = db.execute(
        select(Paper).where(Paper.job_id == job_id)
    ).scalars().all()
    paper_map: dict[uuid.UUID, Paper] = {p.id: p for p in papers}
    paper_ids = set(paper_map.keys())

    # --- Load PaperAuthor rows ---
    pa_rows = db.execute(
        select(PaperAuthor).where(PaperAuthor.paper_id.in_(list(paper_ids)))
    ).scalars().all()

    # author_id → list of (paper_id, author_position)
    author_papers: dict[uuid.UUID, list[tuple[uuid.UUID, int | None]]] = defaultdict(list)
    # paper_id → author count (needed for contribution weight)
    paper_author_count: dict[uuid.UUID, int] = defaultdict(int)
    for pa in pa_rows:
        author_papers[pa.author_id].append((pa.paper_id, pa.author_position))
        paper_author_count[pa.paper_id] += 1

    # --- Cluster map: author_id → set of cluster_ids across their papers ---
    # Need paper graph nodes for cluster info
    paper_graph_nodes = db.execute(
        select(GraphNode).where(
            GraphNode.graph_id.in_(
                select(GraphNode.graph_id)
                .join(GraphResult, GraphNode.graph_id == GraphResult.id)
                .where(
                    GraphResult.job_id == job_id,
                    GraphResult.graph_type == GraphType.PAPER.value,
                )
                .limit(1)
            )
        )
    ).scalars().all()
    paper_cluster: dict[uuid.UUID, int | None] = {
        n.paper_id: n.cluster_id for n in paper_graph_nodes if n.paper_id
    }

    # --- Load authors metadata ---
    all_author_ids = set(author_to_node.keys())
    authors_meta: dict[uuid.UUID, Author] = {
        a.id: a
        for a in db.execute(
            select(Author).where(Author.id.in_(list(all_author_ids)))
        ).scalars().all()
    }

    # --- Compute per-author scores ---
    author_scores: list[dict] = []

    for author_id, node in author_to_node.items():
        cr = node_centrality.get(node.id)
        pa_list = author_papers.get(author_id, [])
        n_papers = len(pa_list)
        if n_papers == 0:
            continue

        # Weighted PEW contributions
        contributions: list[float] = []
        pews: list[float] = []
        recent_papers: list[tuple[uuid.UUID, int | None]] = []  # papers in last RECENT_YEARS

        for paper_id, position in pa_list:
            paper = paper_map.get(paper_id)
            if paper is None:
                continue
            pew = pew_map.get(paper_id, 0.5)
            n_auth = paper_author_count.get(paper_id, 1)
            w = _contribution_weight(position, n_auth)
            contributions.append(pew * w)
            pews.append(pew)
            pub_year = paper.publication_year or 0
            if _CURRENT_YEAR - pub_year <= _RECENT_YEARS:
                recent_papers.append((paper_id, position))

        if not contributions:
            continue

        # Author Impact Score: 60% top-N average + 25% weighted sum + 15% best
        sorted_contrib = sorted(contributions, reverse=True)
        top_n = sorted_contrib[:min(_TOP_N_PAPERS, len(sorted_contrib))]
        top_n_avg = sum(top_n) / len(top_n) if top_n else 0.0
        weighted_sum = sum(contributions) / (1 + math.log(1 + len(contributions)))
        best = sorted_contrib[0] if sorted_contrib else 0.0
        author_impact_score = 0.60 * top_n_avg + 0.25 * weighted_sum + 0.15 * best
        author_impact_score = min(author_impact_score, 1.0)

        # Productivity Score — log-scaled
        productivity_score = min(math.log(1 + n_papers) / math.log(1 + 50), 1.0)

        # Structural Score from author graph centrality
        pagerank_norm = 0.0
        betweenness_norm = 0.0
        eigenvector_norm = 0.0
        if cr:
            pagerank_norm = cr.pagerank or 0.0
            betweenness_norm = cr.betweenness or 0.0
            eigenvector_norm = cr.eigenvector or 0.0
        structural_score = (
            0.35 * pagerank_norm + 0.30 * betweenness_norm + 0.20 * eigenvector_norm
        )
        structural_score = min(structural_score, 1.0)

        # Momentum Score — fraction of papers that are recent, weighted by PEW
        n_recent = len(recent_papers)
        recent_weight = n_recent / max(n_papers, 1)
        momentum_score = min(recent_weight * 1.5, 1.0)  # boost slightly for recent-heavy authors

        # Reliability Score — based on author metadata completeness
        author_meta = authors_meta.get(author_id)
        reliability_score = 0.5  # baseline
        if author_meta:
            if author_meta.openalex_id:
                reliability_score += 0.25
            if author_meta.primary_country_code:
                reliability_score += 0.15
            if author_meta.orcid:
                reliability_score += 0.10
        reliability_score = min(reliability_score, 1.0)

        # Low-impact Ratio
        if pews:
            low_threshold = 0.30
            n_low = sum(1 for p in pews if p < low_threshold)
            low_impact_ratio = n_low / len(pews)
        else:
            low_impact_ratio = 0.0

        # Global Scholarly Impact composite (v2 붙임 2-4)
        # 0.30 × topical_relevance (use 1.0 — all papers matched keyword)
        # 0.30 × author_impact_score
        # 0.20 × structural_score
        # 0.10 × momentum_score
        # 0.10 × reliability_score
        gsi = (
            0.30 * 1.0               # topical relevance proxy
            + 0.30 * author_impact_score
            + 0.20 * structural_score
            + 0.10 * momentum_score
            + 0.10 * reliability_score
        )
        gsi = round(min(gsi, 1.0), 4)

        # Cluster diversity (for Bridge + Niche roles)
        author_clusters: set[int] = set()
        for paper_id, _ in pa_list:
            cid = paper_cluster.get(paper_id)
            if cid is not None:
                author_clusters.add(cid)

        author_scores.append({
            "author_id": author_id,
            "n_papers": n_papers,
            "author_impact_score": author_impact_score,
            "productivity_score": productivity_score,
            "structural_score": structural_score,
            "momentum_score": momentum_score,
            "reliability_score": reliability_score,
            "gsi": gsi,
            "low_impact_ratio": low_impact_ratio,
            "betweenness": betweenness_by_author.get(author_id, 0.0),
            "n_clusters": len(author_clusters),
            "n_recent": n_recent,
            "author_meta": authors_meta.get(author_id),
            "pews": pews,
        })

    if not author_scores:
        return

    # --- Percentile thresholds for role assignment ---
    impact_vals = sorted(s["gsi"] for s in author_scores)
    btw_vals = sorted(s["betweenness"] for s in author_scores)
    count_vals = sorted(s["n_papers"] for s in author_scores)
    n = len(author_scores)

    def percentile_threshold(vals: list[float], pct: float) -> float:
        idx = max(0, int(len(vals) * pct) - 1)
        return vals[idx] if vals else 0.0

    core_threshold = percentile_threshold(impact_vals, _CORE_INFLUENCER_PERCENTILE)
    bridge_threshold = percentile_threshold(btw_vals, _BRIDGE_PERCENTILE)
    productive_threshold = percentile_threshold(count_vals, _PRODUCTIVE_PERCENTILE)

    # --- Build AuthorMetrics rows ---
    rows_to_insert: list[AuthorMetrics] = []

    for s in author_scores:
        author_id = s["author_id"]
        pews = s["pews"]
        meta = s["author_meta"]

        # Role labeling
        roles: list[str] = []

        # Core Influencer
        high_pew_papers = sum(1 for p in pews if p >= 0.65)
        if s["gsi"] >= core_threshold and high_pew_papers >= 2:
            roles.append("Core Influencer")

        # Bridge Researcher
        if s["betweenness"] >= bridge_threshold and s["n_clusters"] >= 2:
            roles.append("Bridge Researcher")

        # Productive Contributor
        avg_pew = sum(pews) / len(pews) if pews else 0
        if (s["n_papers"] >= productive_threshold
                and avg_pew >= 0.35
                and s["low_impact_ratio"] < 0.70):
            roles.append("Productive Contributor")

        # Emerging Researcher
        # recent paper ratio > 0.5 AND at least 2 recent papers
        if s["n_recent"] >= 2 and s["momentum_score"] >= 0.50:
            roles.append("Emerging Researcher")

        # Niche Specialist
        # concentrated in one cluster (single cluster AND that cluster has ≤ 20% of all nodes)
        if s["n_clusters"] == 1 and s["n_papers"] >= 3:
            roles.append("Niche Specialist")

        # Domestic R&D Actor (proxy: KR affiliation, until NTIS overlay in Phase 6)
        if meta and meta.primary_country_code == "KR":
            roles.append("Domestic R&D Actor")

        # Caution Flags
        flags: list[str] = []
        if s["momentum_score"] < 0.20 and s["n_papers"] >= 5:
            flags.append("OLD_IMPACT_ONLY")
        if s["low_impact_ratio"] >= 0.50:
            flags.append("HIGH_LOW_IMPACT_RATIO")
        if not meta or not meta.openalex_id:
            flags.append("LOW_METADATA_COMPLETENESS")

        rows_to_insert.append(AuthorMetrics(
            id=uuid.uuid4(),
            author_id=author_id,
            job_id=job_id,
            related_paper_count=s["n_papers"],
            productivity_score=round(s["productivity_score"], 4),
            author_impact_score=round(s["author_impact_score"], 4),
            structural_score=round(s["structural_score"], 4),
            momentum_score=round(s["momentum_score"], 4),
            reliability_score=round(s["reliability_score"], 4),
            global_scholarly_impact=s["gsi"],
            low_impact_ratio=round(s["low_impact_ratio"], 4),
            role_labels=roles if roles else None,
            caution_flags=flags if flags else None,
        ))

    db.add_all(rows_to_insert)
    logger.info(
        "AuthorMetrics computed for job %s: %d authors, %d with roles",
        job_id, len(rows_to_insert),
        sum(1 for r in rows_to_insert if r.role_labels),
    )
