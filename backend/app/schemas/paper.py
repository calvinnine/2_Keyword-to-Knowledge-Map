import uuid
from datetime import datetime

from pydantic import BaseModel


class PaperListItem(BaseModel):
    id: uuid.UUID
    doi: str | None
    title: str | None
    publication_year: int | None
    venue_name: str | None
    venue_type: str | None
    citation_count: int | None  # null when unverified by Semantic Scholar
    openalex_id: str | None

    model_config = {"from_attributes": True}


class PaperRead(PaperListItem):
    abstract: str | None
    publication_date: str | None
    semantic_scholar_id: str | None
    pubmed_id: str | None
    arxiv_id: str | None
    is_open_access: bool | None
    language: str | None
    fields_of_study: list | None
    sci_classification: str | None
    reference_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
