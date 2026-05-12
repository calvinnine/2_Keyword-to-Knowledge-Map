import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.paper import Paper
from app.schemas.paper import PaperListItem, PaperRead

router = APIRouter()


@router.get("/jobs/{job_id}/papers", response_model=list[PaperListItem])
def list_papers_for_job(
    job_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Paper]:
    stmt = (
        select(Paper)
        .where(Paper.job_id == job_id)
        .order_by(Paper.citation_count.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/papers/{paper_id}", response_model=PaperRead)
def get_paper(paper_id: uuid.UUID, db: Session = Depends(get_db)) -> Paper:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper
