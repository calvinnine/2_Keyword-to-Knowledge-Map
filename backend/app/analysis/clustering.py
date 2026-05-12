"""Community detection / clustering.

Small graphs  (< _LARGE_GRAPH_THRESHOLD nodes): Louvain via python-louvain.
Large graphs  (>= _LARGE_GRAPH_THRESHOLD nodes): Leiden via igraph + leidenalg
  — significantly faster and produces better modularity on sparse networks.

Both paths write to the same ClusterResult / GraphNode schema so downstream
code is unaffected.
"""

import logging
import uuid

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph import GraphResult, GraphNode, GraphEdge, ClusterResult

logger = logging.getLogger(__name__)

_LARGE_GRAPH_THRESHOLD = 5_000  # nodes


def compute_clusters(db: Session, graph_result: GraphResult) -> int:
    """Run community detection on graph_result and persist results.

    Also updates GraphNode.cluster_id and GraphResult.cluster_count.
    Returns the number of ClusterResult rows inserted.
    """
    nodes = db.execute(
        select(GraphNode).where(GraphNode.graph_id == graph_result.id)
    ).scalars().all()
    edges = db.execute(
        select(GraphEdge).where(GraphEdge.graph_id == graph_result.id)
    ).scalars().all()

    if not nodes:
        graph_result.cluster_count = 0
        return 0

    G = nx.Graph()
    G.add_nodes_from(str(n.id) for n in nodes)
    for e in edges:
        a, b = str(e.source_node_id), str(e.target_node_id)
        if G.has_edge(a, b):
            G[a][b]["weight"] += float(e.weight or 1.0)
        else:
            G.add_edge(a, b, weight=float(e.weight or 1.0))

    use_large_mode = G.number_of_nodes() >= _LARGE_GRAPH_THRESHOLD

    if G.number_of_edges() == 0:
        partition = {str(n.id): i for i, n in enumerate(nodes)}
        algorithm = "singleton"
    elif use_large_mode:
        partition, algorithm = _leiden_partition(G, nodes)
    else:
        partition, algorithm = _louvain_partition(G, nodes)

    inserted = 0
    node_by_id = {str(n.id): n for n in nodes}
    cluster_ids: set[int] = set()
    for node_key, cluster_id in partition.items():
        node = node_by_id.get(node_key)
        if not node:
            continue
        node.cluster_id = cluster_id
        cluster_ids.add(cluster_id)
        db.add(ClusterResult(
            id=uuid.uuid4(),
            graph_id=graph_result.id,
            node_id=node.id,
            cluster_id=cluster_id,
            algorithm=algorithm,
        ))
        inserted += 1

    graph_result.cluster_count = len(cluster_ids)
    logger.info(
        "Clustering (%s) for graph %s: %d nodes → %d clusters",
        algorithm, graph_result.id, inserted, len(cluster_ids),
    )
    return inserted


# ---------------------------------------------------------------------------
# Louvain (small graphs)
# ---------------------------------------------------------------------------

def _louvain_partition(G: nx.Graph, nodes) -> tuple[dict, str]:
    try:
        import community as community_louvain  # python-louvain
        partition = community_louvain.best_partition(G, weight="weight", random_state=42)
        return partition, "louvain"
    except Exception as exc:
        logger.warning("Louvain failed, falling back to singleton: %s", exc)
        return {str(n.id): 0 for n in nodes}, "singleton_fallback"


# ---------------------------------------------------------------------------
# Leiden (large graphs)
# ---------------------------------------------------------------------------

def _leiden_partition(G: nx.Graph, nodes) -> tuple[dict, str]:
    """Convert NetworkX → igraph, run Leiden, return (partition_dict, algo_name)."""
    try:
        import igraph as ig
        import leidenalg

        nx_nodes = list(G.nodes())
        node_to_idx = {n: i for i, n in enumerate(nx_nodes)}

        ig_edges = [(node_to_idx[u], node_to_idx[v]) for u, v in G.edges()]
        weights = [G[u][v].get("weight", 1.0) for u, v in G.edges()]

        ig_graph = ig.Graph(n=len(nx_nodes), edges=ig_edges, directed=False)
        ig_graph.es["weight"] = weights

        part = leidenalg.find_partition(
            ig_graph,
            leidenalg.ModularityVertexPartition,
            weights="weight",
            seed=42,
        )
        membership = part.membership  # list[int] indexed by igraph vertex index

        partition = {nx_nodes[i]: membership[i] for i in range(len(nx_nodes))}
        return partition, "leiden"

    except ImportError:
        logger.warning("igraph/leidenalg not installed, falling back to Louvain")
        return _louvain_partition(G, nodes)
    except Exception as exc:
        logger.warning("Leiden failed, falling back to Louvain: %s", exc)
        return _louvain_partition(G, nodes)
