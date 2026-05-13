"""Pre-compute graph layout coordinates using NetworkX spring_layout.

Assigns x_pos / y_pos on GraphNode rows in-place (before db.flush).
The coordinates are normalised to [-1, 1] so the frontend can use them
directly regardless of graph size.
"""

import logging
import uuid

import networkx as nx

from app.models.graph import GraphNode

logger = logging.getLogger(__name__)

_SPRING_ITERATIONS_SMALL = 150   # < 500 nodes
_SPRING_ITERATIONS_LARGE = 50    # >= 500 nodes
_SPRING_K_FACTOR = 1.5           # controls spacing


def assign_layout(
    node_id_map: dict[uuid.UUID, "GraphNode"],
    edges: list[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    """Compute spring_layout and write x_pos/y_pos onto each GraphNode.

    Args:
        node_id_map: mapping from entity UUID → GraphNode ORM instance.
        edges: list of (source_entity_uuid, target_entity_uuid) pairs.
               Uses graph-level entity IDs (paper/author/keyword), not node IDs.
    """
    n = len(node_id_map)
    if n == 0:
        return

    G = nx.Graph()
    G.add_nodes_from(str(eid) for eid in node_id_map)
    for src, tgt in edges:
        G.add_edge(str(src), str(tgt))

    iters = _SPRING_ITERATIONS_LARGE if n >= 500 else _SPRING_ITERATIONS_SMALL
    k = _SPRING_K_FACTOR / (n ** 0.5) if n > 1 else 1.0

    try:
        pos = nx.spring_layout(G, k=k, iterations=iters, seed=42)
    except Exception as exc:
        logger.warning("spring_layout failed (%s); skipping layout coords", exc)
        return

    # Normalise to [-1, 1]
    xs = [v[0] for v in pos.values()]
    ys = [v[1] for v in pos.values()]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xrange = max(xmax - xmin, 1e-9)
    yrange = max(ymax - ymin, 1e-9)

    for eid, node in node_id_map.items():
        p = pos.get(str(eid))
        if p is None:
            continue
        node.x_pos = 2.0 * (p[0] - xmin) / xrange - 1.0
        node.y_pos = 2.0 * (p[1] - ymin) / yrange - 1.0

    logger.info("Layout assigned for %d nodes (%d iters)", n, iters)
