import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    COLLECTED = "collected"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    keyword: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True
    )

    # Search parameters
    max_papers: Mapped[int] = mapped_column(Integer, default=20_000)
    year_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # publication_types: comma-separated or stored as JSON
    publication_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Progress tracking
    papers_collected: Mapped[int] = mapped_column(Integer, default=0)
    papers_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Celery task IDs for cancellation
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Claude-generated insight (populated after analysis completes)
    insight: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extra metadata
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
