import csv
import io
import uuid
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

def _load_all_nodes(db: Session, graph_id: uuid.UUID) -> list[GraphNode]:
    return list(
        db.execute(select(GraphNode).where(GraphNode.graph_id == graph_id)).scalars().all()
    )


def _load_all_edges(db: Session, graph_id: uuid.UUID) -> list[GraphEdge]:
    return list(
        db.execute(select(GraphEdge).where(GraphEdge.graph_id == graph_id)).scalars().all()
    )


@router.get("/graphs/{graph_id}/export/gexf")
def export_graph_gexf(
    graph_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export graph as GEXF (Gephi-compatible XML)."""
    graph = db.get(GraphResult, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    nodes = _load_all_nodes(db, graph_id)
    edges = _load_all_edges(db, graph_id)

    root = ET.Element("gexf", {"xmlns": "http://gexf.net/1.3", "version": "1.3"})
    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "description").text = f"{graph.graph_type} graph — job {graph.job_id}"
    graph_el = ET.SubElement(root, "graph", {"defaultedgetype": "undirected"})

    # Attribute declarations
    attrs_el = ET.SubElement(graph_el, "attributes", {"class": "node"})
    ET.SubElement(attrs_el, "attribute", {"id": "0", "title": "cluster_id", "type": "integer"})
    ET.SubElement(attrs_el, "attribute", {"id": "1", "title": "x_pos", "type": "float"})
    ET.SubElement(attrs_el, "attribute", {"id": "2", "title": "y_pos", "type": "float"})

    nodes_el = ET.SubElement(graph_el, "nodes")
    for n in nodes:
        props = n.properties or {}
        label = (
            props.get("title") or props.get("name") or props.get("display") or str(n.id)[:8]
        )
        node_el = ET.SubElement(nodes_el, "node", {"id": str(n.id), "label": str(label)[:120]})
        attvals = ET.SubElement(node_el, "attvalues")
        if n.cluster_id is not None:
            ET.SubElement(attvals, "attvalue", {"for": "0", "value": str(n.cluster_id)})
        if n.x_pos is not None:
            ET.SubElement(attvals, "attvalue", {"for": "1", "value": str(round(n.x_pos, 6))})
        if n.y_pos is not None:
            ET.SubElement(attvals, "attvalue", {"for": "2", "value": str(round(n.y_pos, 6))})
        # Viz position
        if n.x_pos is not None and n.y_pos is not None:
            ET.SubElement(node_el, "{http://gexf.net/1.3/viz}position", {
                "x": str(round(n.x_pos * 1000, 2)),
                "y": str(round(n.y_pos * 1000, 2)),
                "z": "0",
            })

    edges_el = ET.SubElement(graph_el, "edges")
    for e in edges:
        ET.SubElement(edges_el, "edge", {
            "id": str(e.id),
            "source": str(e.source_node_id),
            "target": str(e.target_node_id),
            "weight": str(round(e.weight, 4)),
            "type": e.edge_type or "",
        })

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    filename = f"graph_{graph_id}.gexf"
    return StreamingResponse(
        io.BytesIO(xml_bytes),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/graphs/{graph_id}/export/csv/nodes")
def export_graph_nodes_csv(
    graph_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export graph nodes as CSV."""
    graph = db.get(GraphResult, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    nodes = _load_all_nodes(db, graph_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "cluster_id", "x_pos", "y_pos", "label", "paper_id", "author_id", "keyword_id"])
    for n in nodes:
        props = n.properties or {}
        label = props.get("title") or props.get("name") or props.get("display") or ""
        writer.writerow([
            str(n.id),
            n.cluster_id if n.cluster_id is not None else "",
            round(n.x_pos, 6) if n.x_pos is not None else "",
            round(n.y_pos, 6) if n.y_pos is not None else "",
            str(label)[:200],
            str(n.paper_id) if n.paper_id else "",
            str(n.author_id) if n.author_id else "",
            str(n.keyword_id) if n.keyword_id else "",
        ])

    filename = f"nodes_{graph_id}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/graphs/{graph_id}/export/csv/edges")
def export_graph_edges_csv(
    graph_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export graph edges as CSV."""
    graph = db.get(GraphResult, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    edges = _load_all_edges(db, graph_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "source", "target", "weight", "edge_type"])
    for e in edges:
        writer.writerow([
            str(e.id),
            str(e.source_node_id),
            str(e.target_node_id),
            round(e.weight, 4),
            e.edge_type or "",
        ])

    filename = f"edges_{graph_id}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
