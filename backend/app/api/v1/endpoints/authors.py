import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_non_public
from app.database import get_db
from app.models.author import Author
from app.models.metrics import AuthorMetrics
from app.models.paper import Paper, PaperAuthor
from app.schemas.author import AuthorListItem, AuthorRead

router = APIRouter()

# ---------------------------------------------------------------------------
# Author recommendation schema
# ---------------------------------------------------------------------------

_ALL_ROLES = [
    "Core Influencer",
    "Bridge Researcher",
    "Productive Contributor",
    "Emerging Researcher",
    "Niche Specialist",
    "Domestic R&D Actor",
]


class AuthorRecommendation(BaseModel):
    author_id: uuid.UUID
    name: str
    primary_country_code: str | None
    primary_country_name: str | None
    openalex_id: str | None
    related_paper_count: int
    global_scholarly_impact: float | None
    author_impact_score: float | None
    structural_score: float | None
    momentum_score: float | None
    low_impact_ratio: float | None
    role_labels: list[str]
    caution_flags: list[str]

    model_config = {"from_attributes": True}


@router.get("/jobs/{job_id}/authors", response_model=list[AuthorListItem])
def list_authors_for_job(
    job_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Author]:
    stmt = (
        select(Author)
        .join(PaperAuthor, PaperAuthor.author_id == Author.id)
        .join(Paper, Paper.id == PaperAuthor.paper_id)
        .where(Paper.job_id == job_id)
        .distinct()
        .order_by(Author.citation_count.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/jobs/{job_id}/author-recommendations",
    response_model=list[AuthorRecommendation],
    # Access grade: Verified Professional (role labels + detailed scores)
    dependencies=[Depends(require_non_public)],
)
def get_author_recommendations(
    job_id: uuid.UUID,
    role: str | None = Query(None, description="Filter by role label (e.g. 'Core Influencer')"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[AuthorRecommendation]:
    """Return authors ranked by Global Scholarly Impact with optional role filter.

    If role is omitted, returns all authors that have at least one role label.
    """
    stmt = (
        select(AuthorMetrics, Author)
        .join(Author, Author.id == AuthorMetrics.author_id)
        .where(AuthorMetrics.job_id == job_id)
    )
    if role:
        # JSONB contains operator — check if the role appears in the array
        stmt = stmt.where(AuthorMetrics.role_labels.contains([role]))
    else:
        stmt = stmt.where(AuthorMetrics.role_labels.isnot(None))

    stmt = stmt.order_by(AuthorMetrics.global_scholarly_impact.desc()).limit(limit)

    rows = db.execute(stmt).all()
    result: list[AuthorRecommendation] = []
    for metrics, author in rows:
        result.append(AuthorRecommendation(
            author_id=author.id,
            name=author.name,
            primary_country_code=author.primary_country_code,
            primary_country_name=author.primary_country_name,
            openalex_id=author.openalex_id,
            related_paper_count=metrics.related_paper_count,
            global_scholarly_impact=metrics.global_scholarly_impact,
            author_impact_score=metrics.author_impact_score,
            structural_score=metrics.structural_score,
            momentum_score=metrics.momentum_score,
            low_impact_ratio=metrics.low_impact_ratio,
            role_labels=metrics.role_labels or [],
            caution_flags=metrics.caution_flags or [],
        ))
    return result


@router.get("/authors/{author_id}", response_model=AuthorRead)
def get_author(author_id: uuid.UUID, db: Session = Depends(get_db)) -> Author:
    author = db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author
