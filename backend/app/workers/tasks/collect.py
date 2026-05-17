"""Collection task: fetch raw payloads from external sources.

Multi-term search
-----------------
When a job has `params.search_terms`, we search each term independently
and deduplicate by source_id so the normaliser sees clean data.

Source limits
- OpenAlex   : searches ALL expanded terms (generous rate limit)
- Semantic Scholar : searches TOP 2 terms only (strict rate limit)
"""

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

# Maximum expanded terms sent to each source.
_OA_MAX_TERMS = 6   # OA is lenient; search all
_S2_MAX_TERMS = 2   # S2 is rate-limited; top 2 only


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

        # Idempotency: if this task is re-run (manual retry / queue redelivery)
        # we wipe any partial raw_payloads from previous attempts so the in-memory
        # `seen_ids` dedup gives us a clean slate. Without this, partial data
        # accumulated across retries breaks the downstream uniqueness constraint
        # on (papers.doi, papers.job_id).
        deleted = db.execute(
            RawPayload.__table__.delete().where(RawPayload.job_id == job_uuid)
        ).rowcount
        if deleted:
            logger.info("collect_papers cleanup: deleted %d stale raw_payloads for job %s",
                        deleted, job_uuid)
        db.commit()

        # Resolve search terms: use params.search_terms if present, else job.keyword
        params = job.params or {}
        search_terms: list[str] = params.get("search_terms") or [job.keyword]

        oa_terms = search_terms[:_OA_MAX_TERMS]
        s2_terms = search_terms[:_S2_MAX_TERMS]

        # OpenAlex is the primary source — failure here is fatal.
        oa_count = _collect_openalex(db, job, oa_terms)

        # Semantic Scholar is supplementary. If it 429s under load or the
        # API key is missing/throttled, we degrade gracefully: keep the OA
        # data, log the issue on the job, and continue the pipeline.
        s2_count = 0
        s2_error: str | None = None
        try:
            s2_count = _collect_semantic_scholar(db, job, s2_terms)
        except Exception as s2_exc:
            logger.warning("S2 collection failed for job %s (continuing OA-only): %s",
                           job.id, s2_exc)
            s2_error = f"semantic_scholar: {s2_exc}"[:500]
            # Roll back any partial S2 transaction so OA data isn't affected.
            db.rollback()
            # Re-attach job to a fresh session state
            job = db.get(AnalysisJob, job_uuid)

        job.papers_collected = oa_count + s2_count
        job.status = JobStatus.COLLECTED
        # Record degradation for visibility in the UI
        if s2_error:
            existing_params = job.params or {}
            existing_params["s2_collection_skipped"] = s2_error
            job.params = {**existing_params}
        db.commit()

        return {
            "job_id": job_id,
            "openalex": oa_count,
            "semantic_scholar": s2_count,
            "search_terms": search_terms,
        }
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


def _collect_openalex(db, job: AnalysisJob, search_terms: list[str]) -> int:
    """Search OpenAlex for each term; deduplicate by source_id across terms."""
    seen_ids: set[str] = set()
    total = 0
    pending: list[RawPayload] = []

    # Distribute max_papers evenly across terms (at least 1 per term)
    per_term = max(1, job.max_papers // len(search_terms))

    with OpenAlexCollector() as collector:
        for term_idx, term in enumerate(search_terms):
            term_count = 0
            logger.info(
                "OpenAlex collecting term %d/%d %r for job %s",
                term_idx + 1, len(search_terms), term, job.id,
            )
            for item in collector.search(
                keyword=term,
                max_results=per_term,
                year_start=job.year_start,
                year_end=job.year_end,
            ):
                source_id = item.get("id") or ""
                if source_id and source_id in seen_ids:
                    continue  # skip duplicate across terms
                if source_id:
                    seen_ids.add(source_id)

                pending.append(RawPayload(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    source="openalex",
                    source_id=source_id,
                    payload=item,
                ))
                total += 1
                term_count += 1

                if len(pending) >= _BATCH_COMMIT:
                    db.add_all(pending)
                    db.commit()
                    pending.clear()
                    logger.info("OpenAlex progress: %d total for job %s", total, job.id)

            logger.info(
                "OpenAlex term %r: %d new papers (total %d)", term, term_count, total
            )

    if pending:
        db.add_all(pending)
        db.commit()
    return total


def _collect_semantic_scholar(db, job: AnalysisJob, search_terms: list[str]) -> int:
    """Search S2 for each term (top N terms only); deduplicate by source_id."""
    seen_ids: set[str] = set()
    total = 0
    pending: list[RawPayload] = []

    # S2 caps at 1000 results per keyword query; split evenly
    per_term = max(1, 1000 // len(search_terms))

    with SemanticScholarCollector() as collector:
        for term_idx, term in enumerate(search_terms):
            term_count = 0
            logger.info(
                "S2 collecting term %d/%d %r for job %s",
                term_idx + 1, len(search_terms), term, job.id,
            )
            for item in collector.search(
                keyword=term,
                max_results=per_term,
                year_start=job.year_start,
                year_end=job.year_end,
            ):
                source_id = item.get("paperId") or ""
                if source_id and source_id in seen_ids:
                    continue
                if source_id:
                    seen_ids.add(source_id)

                pending.append(RawPayload(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    source="semantic_scholar",
                    source_id=source_id,
                    payload=item,
                ))
                total += 1
                term_count += 1

                if len(pending) >= _BATCH_COMMIT:
                    db.add_all(pending)
                    db.commit()
                    pending.clear()
                    logger.info("S2 progress: %d total for job %s", total, job.id)

            logger.info(
                "S2 term %r: %d new papers (total %d)", term, term_count, total
            )

    if pending:
        db.add_all(pending)
        db.commit()
    return total
