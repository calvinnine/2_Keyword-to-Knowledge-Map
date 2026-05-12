import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.graph import GraphResult, GraphNode, GraphEdge
from app.schemas.graph import (
    GraphEdgeRead,
    GraphNodeRead,
    GraphResultDetail,
    GraphResultRead,
)

router = APIRouter()


@router.get("/jobs/{job_id}/graphs", response_model=list[GraphResultRead])
def list_graphs_for_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[GraphResult]:
    stmt = (
        select(GraphResult)
        .where(GraphResult.job_id == job_id)
        .order_by(GraphResult.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/graphs/{graph_id}", response_model=GraphResultDetail)
def get_graph(
    graph_id: uuid.UUID,
    include_nodes: bool = Query(True),
    include_edges: bool = Query(True),
    node_limit: int = Query(2000, ge=0, le=20_000),
    edge_limit: int = Query(5000, ge=0, le=50_000),
    db: Session = Depends(get_db),
) -> GraphResultDetail:
    graph = db.get(GraphResult, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    nodes: list[GraphNodeRead] = []
    edges: list[GraphEdgeRead] = []
    if include_nodes and node_limit > 0:
        node_rows = db.execute(
            select(GraphNode)
            .where(GraphNode.graph_id == graph_id)
            .limit(node_limit)
        ).scalars().all()
        nodes = [GraphNodeRead.model_validate(n) for n in node_rows]
    if include_edges and edge_limit > 0:
        edge_rows = db.execute(
            select(GraphEdge)
            .where(GraphEdge.graph_id == graph_id)
            .order_by(GraphEdge.weight.desc())
            .limit(edge_limit)
        ).scalars().all()
        edges = [GraphEdgeRead.model_validate(e) for e in edge_rows]

    detail = GraphResultDetail.model_validate(graph)
    detail.nodes = nodes
    detail.edges = edges
    return detail
