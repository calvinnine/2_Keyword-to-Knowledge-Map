"""Paper citation network builder.

Builds a directed graph where:
  - Nodes = papers in the job corpus
  - Edges = citation (citing → cited)

Also derives co-citation and bibliographic coupling as undirected weighted
edges for downstream analysis. These are stored as separate edge_type values
in the same GraphResult to keep graphs separated by type.
"""

import logging
import uuid

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper, Citation, PaperSource
from app.models.graph import GraphResult, GraphNode, GraphEdge, GraphType

logger = logging.getLogger(__name__)

_MIN_COCITATION_THRESHOLD = 2
_MIN_BIBCOUPLING_THRESHOLD = 2

# Embedding similarity config
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_EMBEDDING_SIM_THRESHOLD = 0.80      # cosine similarity cutoff
_EMBEDDING_MAX_PAPERS = 500          # cap for large jobs (top N by citation count)
_EMBEDDING_MAX_NEIGHBORS = 5         # max embedding edges per paper


def _scope_filter(scope: str):
    """Return SQLAlchemy filter clause for sci_classification based on scope."""
    from sqlalchemy import or_
    if scope == "sci_ssci":
        return Paper.sci_classification.in_(["SCIE", "SSCI"])
    if scope == "scie":
        return Paper.sci_classification == "SCIE"
    return None  # "all" — no filter


def build_paper_graph(
    db: Session, job_id: uuid.UUID, publication_scope: str = "all"
) -> GraphResult:
    """Build the paper citation graph for a job and persist it."""

    # Load papers for this job, filtered by publication_scope
    stmt = select(Paper).where(Paper.job_id == job_id)
    scope_clause = _scope_filter(publication_scope)
    if scope_clause is not None:
        stmt = stmt.where(scope_clause)
    papers = db.execute(stmt).scalars().all()
    paper_ids = {p.id for p in papers}
    paper_id_to_node: dict[uuid.UUID, uuid.UUID] = {}

    graph_result = GraphResult(
        id=uuid.uuid4(),
        job_id=job_id,
        graph_type=GraphType.PAPER,
        build_params={"min_cocitation": _MIN_COCITATION_THRESHOLD,
                      "min_bibcoupling": _MIN_BIBCOUPLING_THRESHOLD},
    )
    db.add(graph_result)
    db.flush()

    # Create nodes
    for paper in papers:
        node = GraphNode(
            id=uuid.uuid4(),
            graph_id=graph_result.id,
            paper_id=paper.id,
            properties={
                "title": paper.title,
                "year": paper.publication_year,
                "citation_count": paper.citation_count,
            },
        )
        db.add(node)
        paper_id_to_node[paper.id] = node.id

    db.flush()

    # Load citations within corpus
    citations = db.execute(
        select(Citation).where(
            Citation.citing_paper_id.in_(paper_ids),
            Citation.cited_paper_id.in_(paper_ids),
        )
    ).scalars().all()

    # Build NetworkX digraph for co-citation / bib-coupling derivation
    G = nx.DiGraph()
    G.add_nodes_from(str(pid) for pid in paper_ids)

    direct_edges: list[tuple[uuid.UUID, uuid.UUID]] = []
    for cit in citations:
        src = paper_id_to_node.get(cit.citing_paper_id)
        tgt = paper_id_to_node.get(cit.cited_paper_id)
        if src and tgt:
            db.add(GraphEdge(
                id=uuid.uuid4(),
                graph_id=graph_result.id,
                source_node_id=src,
                target_node_id=tgt,
                weight=1.0,
                edge_type="citation",
            ))
            G.add_edge(str(cit.citing_paper_id), str(cit.cited_paper_id))
            direct_edges.append((cit.citing_paper_id, cit.cited_paper_id))

    edge_count = len(direct_edges)

    # Co-citation: two papers cited together frequently
    co_cite_count = _count_cocitations(G, paper_ids)
    for (p1, p2), weight in co_cite_count.items():
        if weight >= _MIN_COCITATION_THRESHOLD:
            n1 = paper_id_to_node.get(p1)
            n2 = paper_id_to_node.get(p2)
            if n1 and n2:
                db.add(GraphEdge(
                    id=uuid.uuid4(),
                    graph_id=graph_result.id,
                    source_node_id=n1,
                    target_node_id=n2,
                    weight=float(weight),
                    edge_type="co_citation",
                ))
                edge_count += 1

    # Bibliographic coupling: two papers share common references
    bib_count = _count_bibliographic_coupling(G, paper_ids)
    for (p1, p2), weight in bib_count.items():
        if weight >= _MIN_BIBCOUPLING_THRESHOLD:
            n1 = paper_id_to_node.get(p1)
            n2 = paper_id_to_node.get(p2)
            if n1 and n2:
                db.add(GraphEdge(
                    id=uuid.uuid4(),
                    graph_id=graph_result.id,
                    source_node_id=n1,
                    target_node_id=n2,
                    weight=float(weight),
                    edge_type="bibliographic_coupling",
                ))
                edge_count += 1

    # Embedding similarity edges (abstract-level semantic proximity)
    emb_count = _add_embedding_edges(db, graph_result, papers, paper_id_to_node)
    edge_count += emb_count

    graph_result.node_count = len(papers)
    graph_result.edge_count = edge_count
    graph_result.stats = {
        "direct_citations": len(direct_edges),
        "co_citation_edges": sum(1 for w in co_cite_count.values() if w >= _MIN_COCITATION_THRESHOLD),
        "bib_coupling_edges": sum(1 for w in bib_count.values() if w >= _MIN_BIBCOUPLING_THRESHOLD),
        "embedding_similarity_edges": emb_count,
    }

    logger.info(
        "Paper graph for job %s: %d nodes, %d edges (%d embedding)",
        job_id, graph_result.node_count, graph_result.edge_count, emb_count,
    )
    return graph_result


def _count_cocitations(G: nx.DiGraph, paper_ids: set[uuid.UUID]) -> dict[tuple, int]:
    """Count how often two papers are both cited by the same third paper."""
    counts: dict[tuple, int] = {}
    pid_strs = {str(p) for p in paper_ids}
    for node in pid_strs:
        predecessors = list(G.predecessors(node))
        for i, a in enumerate(predecessors):
            for b in predecessors[i + 1:]:
                key = (uuid.UUID(a), uuid.UUID(b)) if a < b else (uuid.UUID(b), uuid.UUID(a))
                counts[key] = counts.get(key, 0) + 1
    return counts


def _add_embedding_edges(
    db: Session,
    graph_result: GraphResult,
    papers: list,
    paper_id_to_node: dict[uuid.UUID, uuid.UUID],
) -> int:
    """Compute abstract embedding similarity and add high-similarity edges.

    Uses sentence-transformers (all-MiniLM-L6-v2). Skips gracefully if the
    library is not installed. Returns the number of edges added.
    """
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.info("sentence-transformers not installed; skipping embedding edges")
        return 0

    papers_with_abstract = [p for p in papers if p.abstract and len(p.abstract) > 50]
    if len(papers_with_abstract) < 2:
        return 0

    # For large jobs, cap at top-N papers by citation count to stay tractable
    if len(papers_with_abstract) > _EMBEDDING_MAX_PAPERS:
        papers_with_abstract = sorted(
            papers_with_abstract,
            key=lambda p: p.citation_count or 0,
            reverse=True,
        )[:_EMBEDDING_MAX_PAPERS]

    try:
        model = SentenceTransformer(_EMBEDDING_MODEL)
        abstracts = [p.abstract for p in papers_with_abstract]
        embeddings = model.encode(abstracts, batch_size=64, show_progress_bar=False)

        # L2-normalise for cosine similarity via dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-9)
        sim_matrix = embeddings @ embeddings.T  # shape: (n, n)

        added = 0
        n = len(papers_with_abstract)
        for i in range(n):
            sims = sim_matrix[i].copy()
            sims[i] = -1.0  # exclude self

            top_indices = np.argsort(sims)[::-1][:_EMBEDDING_MAX_NEIGHBORS]
            for j in top_indices:
                if sims[j] < _EMBEDDING_SIM_THRESHOLD:
                    break
                if j <= i:
                    # Only insert each undirected pair once (i < j)
                    continue
                n_i = paper_id_to_node.get(papers_with_abstract[i].id)
                n_j = paper_id_to_node.get(papers_with_abstract[j].id)
                if n_i and n_j:
                    db.add(GraphEdge(
                        id=uuid.uuid4(),
                        graph_id=graph_result.id,
                        source_node_id=n_i,
                        target_node_id=n_j,
                        weight=float(sims[j]),
                        edge_type="embedding_similarity",
                    ))
                    added += 1

        logger.info(
            "Embedding edges for graph %s: %d papers encoded, %d edges added",
            graph_result.id, n, added,
        )
        return added

    except Exception as exc:
        logger.warning("Embedding edge computation failed (skipping): %s", exc)
        return 0


def _count_bibliographic_coupling(G: nx.DiGraph, paper_ids: set[uuid.UUID]) -> dict[tuple, int]:
    """Count how many references two papers share."""
    counts: dict[tuple, int] = {}
    pid_strs = {str(p) for p in paper_ids}
    # Build references map
    refs: dict[str, set[str]] = {n: set(G.successors(n)) for n in pid_strs}
    pid_list = list(pid_strs)
    for i, a in enumerate(pid_list):
        for b in pid_list[i + 1:]:
            shared = len(refs.get(a, set()) & refs.get(b, set()))
            if shared > 0:
                key = (uuid.UUID(a), uuid.UUID(b)) if a < b else (uuid.UUID(b), uuid.UUID(a))
                counts[key] = shared
    return counts
