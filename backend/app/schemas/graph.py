import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.graph import GraphType


class CentralityRead(BaseModel):
    node_id: uuid.UUID
    pagerank: float | None
    eigenvector: float | None
    degree: int | None
    weighted_degree: float | None
    betweenness: float | None
    closeness: float | None

    model_config = {"from_attributes": True}


class GraphNodeRead(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID | None
    author_id: uuid.UUID | None
    keyword_id: uuid.UUID | None
    cluster_id: int | None
    properties: dict[str, Any] | None

    model_config = {"from_attributes": True}


class GraphEdgeRead(BaseModel):
    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    weight: float
    edge_type: str | None

    model_config = {"from_attributes": True}


class GraphResultRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    graph_type: GraphType
    node_count: int
    edge_count: int
    cluster_count: int
    stats: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphResultDetail(GraphResultRead):
    nodes: list[GraphNodeRead] = []
    edges: list[GraphEdgeRead] = []
    build_params: dict[str, Any] | None

    model_config = {"from_attributes": True}
