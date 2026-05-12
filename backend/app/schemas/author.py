import uuid
from datetime import datetime

from pydantic import BaseModel


class AffiliationRead(BaseModel):
    institution_id: uuid.UUID | None
    raw_affiliation: str | None
    country_code: str | None
    country_name: str | None

    model_config = {"from_attributes": True}


class AuthorListItem(BaseModel):
    id: uuid.UUID
    name: str
    openalex_id: str | None
    paper_count: int
    citation_count: int

    model_config = {"from_attributes": True}


class AuthorRead(AuthorListItem):
    semantic_scholar_id: str | None
    orcid: str | None
    primary_country_code: str | None
    primary_country_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
