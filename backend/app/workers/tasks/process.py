"""Processing task: convert raw payloads → canonical entities."""

import logging
import uuid

from sqlalchemy import select

from app.database import SessionLocal
from app.models.job import AnalysisJob, JobStatus
from app.models.raw import RawPayload
from app.models.paper import Paper
from app.processing.ingestion import IngestionService
from app.processing.sci_classifier import classify_papers
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_BATCH_COMMIT = 200


@celery_app.task(name="k2km.process_papers", bind=True)
def process_papers(self, job_id: str) -> dict:
    job_uuid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_uuid)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.status = JobStatus.PROCESSING
        db.commit()

        service = IngestionService(db, job_uuid)
        processed = 0
        deduped = 0

        # Process OpenAlex first (richer affiliation data → preferred canonical source)
        for source, processor in [
            ("openalex", service.process_openalex_payload),
            ("semantic_scholar", service.process_s2_payload),
        ]:
            raws = db.execute(
                select(RawPayload)
                .where(RawPayload.job_id == job_uuid, RawPayload.source == source)
            ).scalars()

            batch_size = 0
            for raw in raws:
                paper = processor(raw)
                if paper is None:
                    deduped += 1
                else:
                    processed += 1
                batch_size += 1
                if batch_size >= _BATCH_COMMIT:
                    db.commit()
                    batch_size = 0
            db.commit()

        # Citation resolution pass (OpenAlex only — S2 references would need a separate pass)
        oa_raws = db.execute(
            select(RawPayload).where(
                RawPayload.job_id == job_uuid,
                RawPayload.source == "openalex",
            )
        ).scalars()
        from app.models.paper import PaperSource
        citation_count = 0
        for raw in oa_raws:
            ps = db.execute(
                select(PaperSource)
                .join(Paper, Paper.id == PaperSource.paper_id)
                .where(
                    PaperSource.source == "openalex",
                    PaperSource.source_id == raw.source_id,
                    Paper.job_id == job_uuid,
                )
            ).scalar_one_or_none()
            if ps:
                citation_count += service.resolve_openalex_citations(raw.payload, ps.paper_id)
        db.commit()

        # Update author primary country (majority vote over affiliations)
        country_updated = service.update_author_primary_countries()
        db.commit()

        # SCI/SSCI/ESCI classification (heuristic, best-effort)
        sci_classified = classify_papers(db, job_uuid)

        # Aggregate author paper_count / citation_count
        service.update_author_stats()
        # Aggregate keyword paper_count
        service.update_keyword_stats()
        db.commit()

        job.papers_processed = processed
        job.status = JobStatus.PROCESSED
        db.commit()

        logger.info(
            "Processed job %s: %d papers, %d duplicates skipped, %d citations resolved, %d sci-classified",
            job_id, processed, deduped, citation_count, sci_classified,
        )
        return {
            "job_id": job_id,
            "processed": processed,
            "deduped": deduped,
            "citations": citation_count,
            "sci_classified": sci_classified,
        }
    except Exception as exc:
        logger.exception("process_papers failed for job %s", job_id)
        db.rollback()
        job = db.get(AnalysisJob, job_uuid)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"process: {exc}"
            db.commit()
        raise
    finally:
        db.close()
