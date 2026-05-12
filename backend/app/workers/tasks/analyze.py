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

        results = {}
        for label, builder in [
            ("paper", build_paper_graph),
            ("author", build_author_graph),
            ("keyword", build_keyword_graph),
        ]:
            graph = builder(db, job_uuid)
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
