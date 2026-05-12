"""Collection task: fetch raw payloads from external sources."""

import logging
import uuid
from datetime import datetime

from app.collectors import OpenAlexCollector, SemanticScholarCollector
from app.database import SessionLocal
from app.models.job import AnalysisJob, JobStatus
from app.models.raw import RawPayload
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_BATCH_COMMIT = 500


@celery_app.task(name="k2km.collect_papers", bind=True)
def collect_papers(self, job_id: str) -> dict:
    """Fetch papers from OpenAlex and Semantic Scholar for this job.

    Stores everything as RawPayload rows. Canonicalization happens later.
    """
    job_uuid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_uuid)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.status = JobStatus.COLLECTING
        db.commit()

        oa_count = _collect_openalex(db, job)
        s2_count = _collect_semantic_scholar(db, job)

        job.papers_collected = oa_count + s2_count
        job.status = JobStatus.COLLECTED
        db.commit()

        return {"job_id": job_id, "openalex": oa_count, "semantic_scholar": s2_count}
    except Exception as exc:
        logger.exception("collect_papers failed for job %s", job_id)
        db.rollback()
        job = db.get(AnalysisJob, job_uuid)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"collect: {exc}"
            db.commit()
        raise
    finally:
        db.close()


def _collect_openalex(db, job: AnalysisJob) -> int:
    count = 0
    pending: list[RawPayload] = []
    with OpenAlexCollector() as collector:
        for item in collector.search(
            keyword=job.keyword,
            max_results=job.max_papers,
            year_start=job.year_start,
            year_end=job.year_end,
        ):
            pending.append(RawPayload(
                id=uuid.uuid4(),
                job_id=job.id,
                source="openalex",
                source_id=item.get("id") or "",
                payload=item,
            ))
            count += 1
            if len(pending) >= _BATCH_COMMIT:
                db.add_all(pending)
                db.commit()
                pending.clear()
                logger.info("OpenAlex progress: %d for job %s", count, job.id)
    if pending:
        db.add_all(pending)
        db.commit()
    return count


def _collect_semantic_scholar(db, job: AnalysisJob) -> int:
    count = 0
    pending: list[RawPayload] = []
    with SemanticScholarCollector() as collector:
        for item in collector.search(
            keyword=job.keyword,
            max_results=job.max_papers,
            year_start=job.year_start,
            year_end=job.year_end,
        ):
            pending.append(RawPayload(
                id=uuid.uuid4(),
                job_id=job.id,
                source="semantic_scholar",
                source_id=item.get("paperId") or "",
                payload=item,
            ))
            count += 1
            if len(pending) >= _BATCH_COMMIT:
                db.add_all(pending)
                db.commit()
                pending.clear()
                logger.info("S2 progress: %d for job %s", count, job.id)
    if pending:
        db.add_all(pending)
        db.commit()
    return count
