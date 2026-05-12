import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.job import JobStatus


class JobCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)
    max_papers: int = Field(default=20_000, ge=100, le=50_000)
    year_start: int | None = Field(default=None, ge=1900, le=2100)
    year_end: int | None = Field(default=None, ge=1900, le=2100)
    publication_types: list[str] | None = None

    @model_validator(mode="after")
    def validate_year_range(self) -> "JobCreate":
        if self.year_start and self.year_end and self.year_start > self.year_end:
            raise ValueError("year_start must be <= year_end")
        return self


class JobFromQuery(BaseModel):
    """Create a job from a natural-language question.

    The query is parsed into a keyword + intent + optional year range.
    Overrides allow the caller to pin specific parameters explicitly.
    """

    query: str = Field(..., min_length=1, max_length=1000)
    # Optional explicit overrides (applied after parsing)
    max_papers: int | None = Field(default=None, ge=100, le=50_000)
    year_start: int | None = Field(default=None, ge=1900, le=2100)
    year_end: int | None = Field(default=None, ge=1900, le=2100)
    publication_types: list[str] | None = None


class ParsedQueryRead(BaseModel):
    keyword: str
    intent: str
    year_start: int | None
    year_end: int | None
    raw_query: str


class JobStatusUpdate(BaseModel):
    status: JobStatus
    error_message: str | None = None
    papers_collected: int | None = None
    papers_processed: int | None = None


class JobListItem(BaseModel):
    id: uuid.UUID
    keyword: str
    status: JobStatus
    max_papers: int
    papers_collected: int
    papers_processed: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobRead(JobListItem):
    year_start: int | None
    year_end: int | None
    publication_types: list[str] | None
    error_message: str | None
    completed_at: datetime | None
    params: dict[str, Any] | None
    insight: str | None = None

    model_config = {"from_attributes": True}
