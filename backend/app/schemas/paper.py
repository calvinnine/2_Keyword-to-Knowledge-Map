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
    # Headline citation count. NULL when neither S2 nor OA-sane produced a value.
    citation_count: int | None
    # Which source produced the headline count: 's2' | 'openalex' | None.
    citation_source: str | None = None
    # S2-only: AI-classified "core" citations (Methods/Results refs).
    influential_citation_count: int | None = None
    # Breakdown of citing papers by venue type (from S2 citations.publicationTypes).
    citation_by_journal: int | None = None
    citation_by_preprint: int | None = None
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
