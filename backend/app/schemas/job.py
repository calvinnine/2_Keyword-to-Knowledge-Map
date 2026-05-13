import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.job import JobStatus

_VALID_SCOPES = frozenset({"all", "wos", "scie", "ssci", "ahci", "esci"})


def _validate_scope(value: str) -> None:
    """Validate comma-separated publication scope string.

    Accepts "all" or one-or-more of: wos, scie, ssci, ahci, esci.
    "all" cannot be combined with other values.
    """
    parts = [p.strip().lower() for p in value.split(",") if p.strip()]
    if not parts:
        raise ValueError("publication_scope must not be empty")
    invalid = set(parts) - _VALID_SCOPES
    if invalid:
        raise ValueError(f"Invalid scope value(s): {invalid}. Must be one of {_VALID_SCOPES}")
    if "all" in parts and len(parts) > 1:
        raise ValueError("'all' cannot be combined with other scope values")


class JobCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)
    max_papers: int = Field(default=20_000, ge=100, le=50_000)
    year_start: int | None = Field(default=None, ge=1900, le=2100)
    year_end: int | None = Field(default=None, ge=1900, le=2100)
    publication_types: list[str] | None = None
    publication_scope: str = Field(default="all")

    @model_validator(mode="after")
    def validate_publication_scope(self) -> "JobCreate":
        _validate_scope(self.publication_scope)
        return self

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
    publication_scope: str = Field(default="all")

    @model_validator(mode="after")
    def validate_publication_scope(self) -> "JobFromQuery":
        _validate_scope(self.publication_scope)
        return self


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
    publication_scope: str = "all"
    error_message: str | None
    completed_at: datetime | None
    params: dict[str, Any] | None
    insight: str | None = None

    model_config = {"from_attributes": True}
