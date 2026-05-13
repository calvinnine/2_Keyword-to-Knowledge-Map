"""NTIS overlay API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import AnalysisJob, JobStatus
from app.models.ntis import NtisProject, ComparativeResult
from app.workers.tasks.ntis_overlay import run_ntis_overlay

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NtisOverlayTriggerResponse(BaseModel):
    job_id: uuid.UUID
    task_id: str
    message: str


class NtisProjectSummary(BaseModel):
    id: uuid.UUID
    ntis_project_id: str | None
    title: str | None
    govt_dept: str | None
    research_agency: str | None
    performing_org: str | None
    total_budget: int | None
    start_year: int | None
    end_year: int | None
    status: str | None
    keywords: list | None

    model_config = {"from_attributes": True}


class ComparativeResultItem(BaseModel):
    id: uuid.UUID
    ntis_project_id: uuid.UUID
    matched_paper_id: uuid.UUID | None
    matched_author_id: uuid.UUID | None
    match_type: str
    similarity_score: float | None
    match_details: dict | None

    model_config = {"from_attributes": True}


class NtisOverviewResponse(BaseModel):
    job_id: uuid.UUID
    ntis_project_count: int
    comparative_match_count: int
    projects: list[NtisProjectSummary]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/ntis-overlay", response_model=NtisOverlayTriggerResponse)
def trigger_ntis_overlay(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Trigger NTIS project collection + comparative analysis for a completed job.

    Requires NTIS_API_KEY to be configured; the overlay will still run (and
    compute comparative matches for any previously collected projects) even
    without the key.
    """
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.COMPLETED, JobStatus.ANALYZING):
        raise HTTPException(
            status_code=409,
            detail=f"Job must be completed before running NTIS overlay (current: {job.status})",
        )

    task = run_ntis_overlay.delay(str(job_id))
    return NtisOverlayTriggerResponse(
        job_id=job_id,
        task_id=task.id,
        message="NTIS overlay task queued",
    )


@router.get("/jobs/{job_id}/ntis", response_model=NtisOverviewResponse)
def get_ntis_overview(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return NTIS project summary and comparative match counts for a job."""
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    projects = db.execute(
        select(NtisProject)
        .where(NtisProject.job_id == job_id)
        .order_by(NtisProject.total_budget.desc().nulls_last())
        .limit(100)
    ).scalars().all()

    match_count = db.execute(
        select(func.count()).where(ComparativeResult.job_id == job_id)
    ).scalar_one()

    return NtisOverviewResponse(
        job_id=job_id,
        ntis_project_count=len(projects),
        comparative_match_count=match_count,
        projects=[NtisProjectSummary.model_validate(p) for p in projects],
    )


@router.get("/jobs/{job_id}/ntis/projects/{project_id}", response_model=NtisProjectSummary)
def get_ntis_project(job_id: uuid.UUID, project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.execute(
        select(NtisProject).where(
            NtisProject.id == project_id,
            NtisProject.job_id == job_id,
        )
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="NTIS project not found")
    return NtisProjectSummary.model_validate(project)


@router.get("/jobs/{job_id}/ntis/comparisons", response_model=list[ComparativeResultItem])
def list_comparative_results(
    job_id: uuid.UUID,
    match_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List comparative results for a job with optional match_type filter."""
    stmt = (
        select(ComparativeResult)
        .where(ComparativeResult.job_id == job_id)
        .order_by(ComparativeResult.similarity_score.desc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    if match_type:
        stmt = stmt.where(ComparativeResult.match_type == match_type)

    rows = db.execute(stmt).scalars().all()
    return [ComparativeResultItem.model_validate(r) for r in rows]
