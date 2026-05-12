"""Community detection / clustering.

Default: Louvain modularity (python-louvain).
For larger graphs in future Large Mode, swap in igraph/Leiden behind this interface.
"""

import logging
import uuid

import community as community_louvain  # python-louvain
import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph import GraphResult, GraphNode, GraphEdge, ClusterResult

logger = logging.getLogger(__name__)


def compute_clusters(db: Session, graph_result: GraphResult) -> int:
    """Run Louvain community detection on graph_result and persist results.

    Also updates GraphNode.cluster_id for fast querying and updates
    GraphResult.cluster_count.
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

    if G.number_of_edges() == 0:
        # No edges → every node is its own singleton cluster
        partition = {str(n.id): i for i, n in enumerate(nodes)}
    else:
        try:
            partition = community_louvain.best_partition(G, weight="weight", random_state=42)
        except Exception as exc:
            logger.warning("Louvain failed for graph %s: %s", graph_result.id, exc)
            partition = {str(n.id): 0 for n in nodes}

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
            algorithm="louvain",
        ))
        inserted += 1

    graph_result.cluster_count = len(cluster_ids)
    logger.info(
        "Clustering for graph %s: %d nodes assigned to %d clusters",
        graph_result.id, inserted, len(cluster_ids),
    )
    return inserted
