import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Canonical name after normalization
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    # ISO 3166-1 alpha-2 country code derived from affiliation metadata
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    country_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # External identifiers
    openalex_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    ror_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Extra fields preserved from sources
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
