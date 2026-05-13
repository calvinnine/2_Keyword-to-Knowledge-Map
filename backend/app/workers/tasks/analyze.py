"""Analysis task: build paper/author/keyword graphs, centrality, clustering."""

import logging
import uuid
from datetime import datetime, timezone

from app.analysis import (
    build_paper_graph,
    build_author_graph,
    build_keyword_graph,
    compute_centrality,
    compute_clusters,
    generate_insight,
    compute_paper_metrics,
    compute_author_metrics,
)
from app.database import SessionLocal
from app.models.job import AnalysisJob, JobStatus
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="k2km.analyze_graphs", bind=True)
def analyze_graphs(self, job_id: str) -> dict:
    job_uuid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_uuid)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.status = JobStatus.ANALYZING
        db.commit()

        scope = job.publication_scope or "all"
        results = {}
        paper_graph = None
        author_graph = None

        for label, builder in [
            ("paper", build_paper_graph),
            ("author", build_author_graph),
            ("keyword", build_keyword_graph),
        ]:
            graph = builder(db, job_uuid, publication_scope=scope)
            db.flush()
            compute_centrality(db, graph)
            compute_clusters(db, graph)
            db.commit()
            results[label] = {
                "graph_id": str(graph.id),
                "nodes": graph.node_count,
                "edges": graph.edge_count,
                "clusters": graph.cluster_count,
            }
            if label == "paper":
                paper_graph = graph
            elif label == "author":
                author_graph = graph

        # Paper Evidence Weight + Author metrics / role labeling (Phase 3)
        if paper_graph and author_graph:
            try:
                pew_map = compute_paper_metrics(db, job_uuid, paper_graph)
                db.flush()
                compute_author_metrics(db, job_uuid, author_graph, pew_map)
                db.commit()
                logger.info("PEW + AuthorMetrics computed for job %s", job_id)
            except Exception as exc:
                logger.warning("PEW/AuthorMetrics failed for job %s (non-fatal): %s", job_id, exc)
                db.rollback()

        # Generate Claude insight (best-effort; never fails the job)
        insight = generate_insight(db, job_uuid)
        if insight:
            job.insight = insight

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Analysis complete for job %s: %s", job_id, results)
        return {"job_id": job_id, "graphs": results}
    except Exception as exc:
        logger.exception("analyze_graphs failed for job %s", job_id)
        db.rollback()
        job = db.get(AnalysisJob, job_uuid)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"analyze: {exc}"
            db.commit()
        raise
    finally:
        db.close()
