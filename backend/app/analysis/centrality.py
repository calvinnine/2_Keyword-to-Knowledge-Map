"""Centrality computation across paper/author/keyword graphs.

Per planning report §10:
  - Influence: PageRank, Eigenvector
  - Hub:       Degree, Weighted Degree
  - Bridge:    Betweenness
  - Access:    Closeness

Raw metric values are stored per node. Grouping into meaning categories
is performed at query time so the same data can support multiple UI strategies.
"""

import logging
import uuid

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph import GraphResult, GraphNode, GraphEdge, CentralityResult

logger = logging.getLogger(__name__)

_BETWEENNESS_SAMPLE_THRESHOLD = 2000


def compute_centrality(db: Session, graph_result: GraphResult) -> int:
    """Compute centrality metrics for every node of graph_result.

    Returns the number of CentralityResult rows inserted.
    """
    nodes = db.execute(
        select(GraphNode).where(GraphNode.graph_id == graph_result.id)
    ).scalars().all()
    edges = db.execute(
        select(GraphEdge).where(GraphEdge.graph_id == graph_result.id)
    ).scalars().all()

    if not nodes:
        return 0

    G = nx.Graph()  # undirected for centrality (covers all edge_types)
    node_id_strs = {str(n.id) for n in nodes}
    G.add_nodes_from(node_id_strs)
    for e in edges:
        a = str(e.source_node_id)
        b = str(e.target_node_id)
        if G.has_edge(a, b):
            G[a][b]["weight"] += float(e.weight or 1.0)
        else:
            G.add_edge(a, b, weight=float(e.weight or 1.0))

    # PageRank
    try:
        pagerank = nx.pagerank(G, weight="weight")
    except Exception as exc:
        logger.warning("PageRank failed for graph %s: %s", graph_result.id, exc)
        pagerank = {}

    # Eigenvector centrality (can fail on disconnected graphs)
    try:
        eigenvector = nx.eigenvector_centrality_numpy(G, weight="weight")
    except Exception as exc:
        logger.warning("Eigenvector failed for graph %s: %s", graph_result.id, exc)
        eigenvector = {}

    # Degree & weighted degree
    degree = dict(G.degree())
    weighted_degree = dict(G.degree(weight="weight"))

    # Betweenness (sampled for large graphs)
    try:
        if G.number_of_nodes() > _BETWEENNESS_SAMPLE_THRESHOLD:
            k_sample = min(500, G.number_of_nodes())
            betweenness = nx.betweenness_centrality(G, k=k_sample, weight="weight", seed=42)
        else:
            betweenness = nx.betweenness_centrality(G, weight="weight")
    except Exception as exc:
        logger.warning("Betweenness failed for graph %s: %s", graph_result.id, exc)
        betweenness = {}

    # Closeness (use largest connected component for speed on huge graphs)
    try:
        closeness = nx.closeness_centrality(G)
    except Exception as exc:
        logger.warning("Closeness failed for graph %s: %s", graph_result.id, exc)
        closeness = {}

    inserted = 0
    for node in nodes:
        key = str(node.id)
        db.add(CentralityResult(
            id=uuid.uuid4(),
            graph_id=graph_result.id,
            node_id=node.id,
            pagerank=pagerank.get(key),
            eigenvector=eigenvector.get(key),
            degree=degree.get(key),
            weighted_degree=weighted_degree.get(key),
            betweenness=betweenness.get(key),
            closeness=closeness.get(key),
        ))
        inserted += 1

    logger.info("Centrality computed for graph %s: %d nodes", graph_result.id, inserted)
    return inserted
