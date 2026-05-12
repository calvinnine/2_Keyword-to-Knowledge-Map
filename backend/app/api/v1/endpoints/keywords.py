import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.keyword import Keyword
from app.models.paper import Paper, PaperKeyword
from app.schemas.keyword import KeywordRead

router = APIRouter()


@router.get("/jobs/{job_id}/keywords", response_model=list[KeywordRead])
def list_keywords_for_job(
    job_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Keyword]:
    stmt = (
        select(Keyword)
        .join(PaperKeyword, PaperKeyword.keyword_id == Keyword.id)
        .join(Paper, Paper.id == PaperKeyword.paper_id)
        .where(Paper.job_id == job_id)
        .distinct()
        .order_by(Keyword.paper_count.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())
