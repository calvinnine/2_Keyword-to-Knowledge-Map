"""End-to-end pipeline orchestration: collect → process → analyze.

Exposed as a single Celery chain so the API only needs to enqueue one task.
"""

from celery import chain

from app.workers.celery_app import celery_app
from app.workers.tasks.collect import collect_papers
from app.workers.tasks.process import process_papers
from app.workers.tasks.analyze import analyze_graphs


@celery_app.task(name="k2km.run_pipeline")
def run_pipeline(job_id: str) -> str:
    """Enqueue the full pipeline as a chain and return the chain ID."""
    workflow = chain(
        collect_papers.si(job_id),
        process_papers.si(job_id),
        analyze_graphs.si(job_id),
    )
    result = workflow.apply_async()
    return result.id


def enqueue_pipeline(job_id: str) -> str:
    """Helper for the API layer to start a job pipeline synchronously."""
    workflow = chain(
        collect_papers.si(job_id),
        process_papers.si(job_id),
        analyze_graphs.si(job_id),
    )
    result = workflow.apply_async()
    return result.id
