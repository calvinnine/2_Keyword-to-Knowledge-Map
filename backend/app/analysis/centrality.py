"""Centrality computation across paper/author/keyword graphs.

Per planning report §10:
  - Influence: PageRank, Eigenvector
  - Hub:       Degree, Weighted Degree
  - Bridge:    Betweenness
  - Access:    Closeness

Small graphs  (< _LARGE_GRAPH_THRESHOLD): pure NetworkX.
Large graphs  (>= _LARGE_GRAPH_THRESHOLD): igraph for betweenness & closeness
  (igraph's C-level implementation is 10-100× faster on sparse graphs).
"""

import logging
import uuid

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph import GraphResult, GraphNode, GraphEdge, CentralityResult

logger = logging.getLogger(__name__)

_BETWEENNESS_SAMPLE_THRESHOLD = 300     # full calc only for tiny graphs (hang fix)
_CLOSENESS_SAMPLE_THRESHOLD = 500       # closeness is O(VE); sample on larger graphs
_BETWEENNESS_K = 200
_CLOSENESS_K = 200
_LARGE_GRAPH_THRESHOLD = 5_000          # switch to igraph above this


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

    use_large_mode = G.number_of_nodes() >= _LARGE_GRAPH_THRESHOLD

    # --- Influence ----------------------------------------------------------
    try:
        pagerank = nx.pagerank(G, weight="weight")
    except Exception as exc:
        logger.warning("PageRank failed for graph %s: %s", graph_result.id, exc)
        pagerank = {}

    try:
        eigenvector = nx.eigenvector_centrality_numpy(G, weight="weight")
    except Exception as exc:
        logger.warning("Eigenvector failed for graph %s: %s", graph_result.id, exc)
        eigenvector = {}

    # --- Hub ----------------------------------------------------------------
    degree = dict(G.degree())
    weighted_degree = dict(G.degree(weight="weight"))

    # --- Bridge & Access ----------------------------------------------------
    if use_large_mode:
        betweenness, closeness = _igraph_bridge_access(G)
    else:
        betweenness = _nx_betweenness(G, graph_result.id)
        closeness = _nx_closeness(G, graph_result.id)

    # --- Persist ------------------------------------------------------------
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

    logger.info(
        "Centrality (%s) computed for graph %s: %d nodes",
        "large" if use_large_mode else "standard", graph_result.id, inserted,
    )
    return inserted


# ---------------------------------------------------------------------------
# Standard NetworkX paths (small graphs)
# ---------------------------------------------------------------------------

def _nx_betweenness(G: nx.Graph, graph_id) -> dict:
    try:
        n = G.number_of_nodes()
        if n > _BETWEENNESS_SAMPLE_THRESHOLD:
            k_sample = min(_BETWEENNESS_K, n)
            return nx.betweenness_centrality(G, k=k_sample, weight="weight", seed=42)
        return nx.betweenness_centrality(G, weight="weight")
    except Exception as exc:
        logger.warning("Betweenness failed for graph %s: %s", graph_id, exc)
        return {}


def _nx_closeness(G: nx.Graph, graph_id) -> dict:
    try:
        n = G.number_of_nodes()
        if n > _CLOSENESS_SAMPLE_THRESHOLD:
            sample_nodes = list(G.nodes)[:_CLOSENESS_K]
            return {v: nx.closeness_centrality(G, u=v) for v in sample_nodes}
        return nx.closeness_centrality(G)
    except Exception as exc:
        logger.warning("Closeness failed for graph %s: %s", graph_id, exc)
        return {}


# ---------------------------------------------------------------------------
# igraph paths (large graphs)
# ---------------------------------------------------------------------------

def _igraph_bridge_access(G: nx.Graph) -> tuple[dict, dict]:
    """Compute betweenness and closeness via igraph (much faster for large graphs).

    Falls back to NetworkX sampled betweenness if igraph is not installed.
    """
    try:
        import igraph as ig

        nx_nodes = list(G.nodes())
        node_to_idx = {n: i for i, n in enumerate(nx_nodes)}

        ig_edges = [(node_to_idx[u], node_to_idx[v]) for u, v in G.edges()]
        weights = [G[u][v].get("weight", 1.0) for u, v in G.edges()]

        ig_graph = ig.Graph(n=len(nx_nodes), edges=ig_edges, directed=False)
        ig_graph.es["weight"] = weights

        # igraph betweenness uses 1/weight as distance by default — invert so
        # higher weight = shorter distance (same semantics as NetworkX weight=)
        inv_weights = [1.0 / max(w, 1e-9) for w in weights]
        ig_graph.es["inv_weight"] = inv_weights

        btw_raw = ig_graph.betweenness(weights="inv_weight", directed=False)
        clo_raw = ig_graph.closeness(weights="inv_weight")

        # Normalize betweenness to [0, 1] range (NetworkX convention)
        n = len(nx_nodes)
        norm = (n - 1) * (n - 2) / 2 if n > 2 else 1.0

        betweenness = {nx_nodes[i]: btw_raw[i] / norm for i in range(n)}
        closeness = {nx_nodes[i]: clo_raw[i] for i in range(n)}
        return betweenness, closeness

    except ImportError:
        logger.warning("igraph not installed; falling back to sampled NetworkX betweenness")
        # Reuse nx sampled path — pass a dummy graph_id for logging
        btw = {}
        try:
            k_sample = min(500, G.number_of_nodes())
            btw = nx.betweenness_centrality(G, k=k_sample, weight="weight", seed=42)
        except Exception as exc:
            logger.warning("Fallback betweenness failed: %s", exc)
        clo = {}
        try:
            clo = nx.closeness_centrality(G)
        except Exception as exc:
            logger.warning("Fallback closeness failed: %s", exc)
        return btw, clo

    except Exception as exc:
        logger.warning("igraph centrality failed, falling back to NetworkX: %s", exc)
        btw = _nx_betweenness(G, "fallback")
        clo = _nx_closeness(G, "fallback")
        return btw, clo
