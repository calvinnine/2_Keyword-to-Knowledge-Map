"""Author co-authorship network builder.

Nodes = authors who appear in the job corpus.
Edges = co-authorship (both on the same paper), weight = number of shared papers.
"""

import logging
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper, PaperAuthor
from app.models.author import Author
from app.models.graph import GraphResult, GraphNode, GraphEdge, GraphType

logger = logging.getLogger(__name__)

_MIN_COAUTHORSHIP_WEIGHT = 1


def build_author_graph(db: Session, job_id: uuid.UUID) -> GraphResult:
    """Build co-authorship graph for all authors in job corpus."""

    # Fetch all (paper_id, author_id) pairs for papers in this job
    rows = db.execute(
        select(PaperAuthor.paper_id, PaperAuthor.author_id)
        .where(
            PaperAuthor.paper_id.in_(
                select(Paper.id).where(Paper.job_id == job_id)
            )
        )
    ).all()

    # Build paper → authors map
    paper_to_authors: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    all_author_ids: set[uuid.UUID] = set()
    for paper_id, author_id in rows:
        paper_to_authors[paper_id].append(author_id)
        all_author_ids.add(author_id)

    # Fetch author names
    authors = db.execute(
        select(Author).where(Author.id.in_(all_author_ids))
    ).scalars().all()
    author_map: dict[uuid.UUID, Author] = {a.id: a for a in authors}

    graph_result = GraphResult(
        id=uuid.uuid4(),
        job_id=job_id,
        graph_type=GraphType.AUTHOR,
        build_params={"min_weight": _MIN_COAUTHORSHIP_WEIGHT},
    )
    db.add(graph_result)
    db.flush()

    # Create nodes
    author_to_node: dict[uuid.UUID, uuid.UUID] = {}
    for author in authors:
        node = GraphNode(
            id=uuid.uuid4(),
            graph_id=graph_result.id,
            author_id=author.id,
            properties={
                "name": author.name,
                "paper_count": author.paper_count,
                "citation_count": author.citation_count,
            },
        )
        db.add(node)
        author_to_node[author.id] = node.id

    db.flush()

    # Count co-authorship weights
    coauthor_weights: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    for authors_on_paper in paper_to_authors.values():
        for i, a in enumerate(authors_on_paper):
            for b in authors_on_paper[i + 1:]:
                key = (a, b) if a < b else (b, a)
                coauthor_weights[key] += 1

    edge_count = 0
    for (a, b), weight in coauthor_weights.items():
        if weight < _MIN_COAUTHORSHIP_WEIGHT:
            continue
        n_a = author_to_node.get(a)
        n_b = author_to_node.get(b)
        if n_a and n_b:
            db.add(GraphEdge(
                id=uuid.uuid4(),
                graph_id=graph_result.id,
                source_node_id=n_a,
                target_node_id=n_b,
                weight=float(weight),
                edge_type="co_authorship",
            ))
            edge_count += 1

    graph_result.node_count = len(authors)
    graph_result.edge_count = edge_count
    graph_result.stats = {"total_authors": len(all_author_ids)}

    logger.info(
        "Author graph for job %s: %d nodes, %d edges",
        job_id, graph_result.node_count, graph_result.edge_count,
    )
    return graph_result
