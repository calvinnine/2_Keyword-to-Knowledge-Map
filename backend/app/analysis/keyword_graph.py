"""Keyword co-occurrence network builder.

Nodes = keywords that appear in the job corpus.
Edges = co-occurrence on the same paper, weight = number of shared papers.
"""

import logging
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper, PaperKeyword
from app.models.keyword import Keyword
from app.models.graph import GraphResult, GraphNode, GraphEdge, GraphType

logger = logging.getLogger(__name__)

_MIN_COOCCURRENCE_WEIGHT = 2


def build_keyword_graph(db: Session, job_id: uuid.UUID) -> GraphResult:
    """Build keyword co-occurrence graph."""

    rows = db.execute(
        select(PaperKeyword.paper_id, PaperKeyword.keyword_id)
        .where(
            PaperKeyword.paper_id.in_(
                select(Paper.id).where(Paper.job_id == job_id)
            )
        )
    ).all()

    paper_to_keywords: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    all_keyword_ids: set[uuid.UUID] = set()
    for paper_id, keyword_id in rows:
        paper_to_keywords[paper_id].append(keyword_id)
        all_keyword_ids.add(keyword_id)

    keywords = db.execute(
        select(Keyword).where(Keyword.id.in_(all_keyword_ids))
    ).scalars().all()

    graph_result = GraphResult(
        id=uuid.uuid4(),
        job_id=job_id,
        graph_type=GraphType.KEYWORD,
        build_params={"min_weight": _MIN_COOCCURRENCE_WEIGHT},
    )
    db.add(graph_result)
    db.flush()

    keyword_to_node: dict[uuid.UUID, uuid.UUID] = {}
    for kw in keywords:
        node = GraphNode(
            id=uuid.uuid4(),
            graph_id=graph_result.id,
            keyword_id=kw.id,
            properties={
                "display": kw.display,
                "paper_count": kw.paper_count,
            },
        )
        db.add(node)
        keyword_to_node[kw.id] = node.id

    db.flush()

    cooc_weights: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    for kws_on_paper in paper_to_keywords.values():
        unique_kws = list(set(kws_on_paper))
        for i, a in enumerate(unique_kws):
            for b in unique_kws[i + 1:]:
                key = (a, b) if a < b else (b, a)
                cooc_weights[key] += 1

    edge_count = 0
    for (a, b), weight in cooc_weights.items():
        if weight < _MIN_COOCCURRENCE_WEIGHT:
            continue
        n_a = keyword_to_node.get(a)
        n_b = keyword_to_node.get(b)
        if n_a and n_b:
            db.add(GraphEdge(
                id=uuid.uuid4(),
                graph_id=graph_result.id,
                source_node_id=n_a,
                target_node_id=n_b,
                weight=float(weight),
                edge_type="co_occurrence",
            ))
            edge_count += 1

    graph_result.node_count = len(keywords)
    graph_result.edge_count = edge_count
    graph_result.stats = {"total_keywords": len(all_keyword_ids)}

    logger.info(
        "Keyword graph for job %s: %d nodes, %d edges",
        job_id, graph_result.node_count, graph_result.edge_count,
    )
    return graph_result
