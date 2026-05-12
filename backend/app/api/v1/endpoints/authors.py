import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.author import Author
from app.models.paper import Paper, PaperAuthor
from app.schemas.author import AuthorListItem, AuthorRead

router = APIRouter()


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


@router.get("/authors/{author_id}", response_model=AuthorRead)
def get_author(author_id: uuid.UUID, db: Session = Depends(get_db)) -> Author:
    author = db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author
