import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import AnalysisJob, JobStatus
from app.nlp.query_parser import HeuristicQueryParser
from app.schemas.job import (
    JobCreate,
    JobFromQuery,
    JobListItem,
    JobRead,
    ParsedQueryRead,
)

router = APIRouter()


def _enqueue_pipeline_for_job(db: Session, job: AnalysisJob) -> None:
    """Enqueue the analysis pipeline. Defensive against worker unavailability."""
    try:
        from app.workers.tasks.pipeline import enqueue_pipeline
        task_id = enqueue_pipeline(str(job.id))
        job.celery_task_id = task_id
        db.commit()
        db.refresh(job)
    except Exception as exc:  # pragma: no cover
        job.status = JobStatus.FAILED
        job.error_message = f"enqueue: {exc}"
        db.commit()
        db.refresh(job)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> AnalysisJob:
    """Create an analysis job and enqueue the pipeline asynchronously."""
    job = AnalysisJob(
        keyword=payload.keyword,
        max_papers=payload.max_papers,
        year_start=payload.year_start,
        year_end=payload.year_end,
        publication_types=payload.publication_types,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_pipeline_for_job(db, job)
    return job


@router.post(
    "/parse-query",
    response_model=ParsedQueryRead,
    summary="Preview natural-language → keyword parsing without creating a job",
)
def parse_query(payload: JobFromQuery) -> ParsedQueryRead:
    """Useful for client-side UIs to show the user what keyword will be used
    before they confirm submission of a job.
    """
    parsed = HeuristicQueryParser().parse(payload.query)
    if not parsed.keyword:
        raise HTTPException(
            status_code=422,
            detail="Could not extract a keyword from the query",
        )
    return ParsedQueryRead(
        keyword=parsed.keyword,
        intent=parsed.intent,
        year_start=parsed.year_start,
        year_end=parsed.year_end,
        raw_query=parsed.raw_query,
    )


@router.post(
    "/from-query",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job from a natural-language question (e.g. \"quantum computing 분야에서 누가 잘해?\")",
)
def create_job_from_query(
    payload: JobFromQuery,
    db: Session = Depends(get_db),
) -> AnalysisJob:
    """Translates an NL query → keyword + intent, then runs the same pipeline.

    The analysis core remains keyword-based. The original NL text and the
    detected intent are preserved on `AnalysisJob.params` so downstream views
    can highlight the relevant graph (author / paper / keyword).
    """
    parsed = HeuristicQueryParser().parse(payload.query)
    if not parsed.keyword:
        raise HTTPException(
            status_code=422,
            detail="Could not extract a keyword from the query",
        )

    job = AnalysisJob(
        keyword=parsed.keyword,
        max_papers=payload.max_papers or 20_000,
        year_start=payload.year_start if payload.year_start is not None else parsed.year_start,
        year_end=payload.year_end if payload.year_end is not None else parsed.year_end,
        publication_types=payload.publication_types,
        params=parsed.to_params(),
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_pipeline_for_job(db, job)
    return job


@router.get("", response_model=list[JobListItem])
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: JobStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> list[AnalysisJob]:
    stmt = select(AnalysisJob).order_by(AnalysisJob.created_at.desc())
    if status_filter:
        stmt = stmt.where(AnalysisJob.status == status_filter)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=409, detail=f"Job already {job.status.value}")

    if job.celery_task_id:
        try:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass  # best-effort

    job.status = JobStatus.CANCELLED
    db.commit()
    db.refresh(job)
    return job
