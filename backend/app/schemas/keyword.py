import uuid
from datetime import datetime

from pydantic import BaseModel


class KeywordRead(BaseModel):
    id: uuid.UUID
    normalized: str
    display: str
    paper_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
