"""Celery task: NTIS R&D 과제 수집 + 비교 분석 오버레이.

파이프라인 흐름 (독립 실행 — 메인 collect/process/analyze chain과 별개):
  1. 과제검색 API → NtisProject 적재
  2. 성과검색 API(논문) → 기존 Paper와 ISSN/제목 기반 직접 매핑
  3. comparative analysis (keyword / author / institution 매칭)

트리거: POST /api/v1/jobs/{job_id}/ntis-overlay
       (메인 파이프라인 완료 후 별도 호출)

API 키가 없으면 빈 수집 후 comparative analysis만 실행한다.
"""

import logging
import re
import uuid

from sqlalchemy import select

from app.analysis.comparative import run_comparative_analysis
from app.analysis.domestic_score import compute_domestic_scores
from app.collectors.ntis import NtisCollector, NtisApiError
from app.config import settings
from app.database import SessionLocal
from app.models.job import AnalysisJob, JobStatus
from app.models.ntis import NtisProject, ComparativeResult
from app.models.paper import Paper
from app.processing.ntis_ingestion import NtisIngestionService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_MAX_NTIS_PROJECT_RESULTS = 500
_MAX_NTIS_PAPER_RESULTS = 200


@celery_app.task(name="k2km.ntis_overlay", bind=True)
def run_ntis_overlay(self, job_id: str) -> dict:
    """Collect NTIS projects + paper outcomes and run comparative analysis."""
    job_uuid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_uuid)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        if job.status not in (JobStatus.COMPLETED, JobStatus.ANALYZING):
            raise ValueError(
                f"NTIS overlay requires a completed job; current status: {job.status}"
            )

        # NTIS is a Korean-language index — prefer the original Korean keyword
        # over its English translation when the job was auto-translated.
        keyword = (job.params or {}).get("original_keyword") or job.keyword
        year_start = job.year_start
        year_end = job.year_end

        projects_collected = 0
        paper_direct_matches = 0
        ntis_api_error: str | None = None

        if settings.ntis_api_key:
            service = NtisIngestionService(db, job_uuid)

            try:
                with NtisCollector() as collector:
                    # --- 1. 과제 수집 -------------------------------------------
                    for raw in collector.search_projects(
                        keyword=keyword,
                        max_results=_MAX_NTIS_PROJECT_RESULTS,
                        year_start=year_start,
                        year_end=year_end,
                    ):
                        project = service.ingest_project(raw)
                        if project:
                            projects_collected += 1
                        if projects_collected % 100 == 0 and projects_collected > 0:
                            db.flush()
                    db.commit()
                    logger.info("NTIS projects collected: %d for job %s", projects_collected, job_id)

                    # --- 2. 논문 성과 수집 → 직접 매핑 ----------------------------
                    paper_direct_matches = _collect_and_match_papers(
                        db=db,
                        collector=collector,
                        job_uuid=job_uuid,
                        keyword=keyword,
                        year_start=year_start,
                        year_end=year_end,
                    )
                    db.commit()
            except NtisApiError as exc:
                # NTIS rejected the call (IP whitelist / quota / bad key).
                # Record the message but don't fail the whole task —
                # comparative analysis still runs against whatever projects
                # might already exist for this job.
                ntis_api_error = f"NTIS API: {exc}"
                logger.warning("NTIS API error for job %s: %s", job_id, exc)
                db.rollback()

        else:
            logger.info(
                "NTIS_API_KEY not set; skipping collection for job %s. "
                "Set NTIS_API_KEY in .env and re-trigger.",
                job_id,
            )

        # --- 3. Comparative analysis (keyword/author/institution) ----------
        comparative_count = run_comparative_analysis(db, job_uuid)
        db.commit()

        # --- 4. Domestic R&D Relevance scoring + Strategic Connector label ---
        domestic_updated = 0
        try:
            domestic_updated = compute_domestic_scores(db, job_uuid)
            db.commit()
        except Exception as exc:
            logger.warning(
                "compute_domestic_scores failed for job %s (non-fatal): %s", job_id, exc
            )
            db.rollback()

        result = {
            "job_id": job_id,
            "ntis_projects_collected": projects_collected,
            "paper_direct_matches": paper_direct_matches,
            "comparative_matches": comparative_count,
            "domestic_scores_updated": domestic_updated,
            "ntis_api_error": ntis_api_error,
        }
        # Persist the last-run summary on AnalysisJob.params so the overview
        # API can surface API errors / status to the frontend without needing
        # to query Celery's result backend.
        current_params = dict(job.params or {})
        current_params["ntis_last_run"] = {
            "projects_collected": projects_collected,
            "paper_direct_matches": paper_direct_matches,
            "comparative_matches": comparative_count,
            "error": ntis_api_error,
        }
        job.params = current_params
        db.commit()

        logger.info("NTIS overlay complete for job %s: %s", job_id, result)
        return result

    except Exception as exc:
        logger.exception("ntis_overlay failed for job %s", job_id)
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 성과(논문) 수집 + 직접 매핑
# ---------------------------------------------------------------------------

def _collect_and_match_papers(
    db,
    collector: NtisCollector,
    job_uuid: uuid.UUID,
    keyword: str,
    year_start: int | None,
    year_end: int | None,
) -> int:
    """Collect NTIS paper outcomes and link them to existing K2KM papers.

    Matching strategy (in order):
    1. ISSN match: NtisOutcome.IssnNumber vs Paper.venue_name (via openalex ISSN lookup)
    2. Title normalisation match: NtisOutcome.ResultTitle ~= Paper.title_normalized

    Each match creates a ComparativeResult with match_type='paper_outcome_direct'.
    Returns number of matches inserted.
    """
    # Pre-load K2KM papers for this job (title_normalized for fast lookup)
    papers = db.execute(
        select(Paper).where(Paper.job_id == job_uuid)
    ).scalars().all()

    if not papers:
        return 0

    title_norm_index: dict[str, uuid.UUID] = {
        p.title_normalized: p.id
        for p in papers
        if p.title_normalized
    }

    # Pre-load all NtisProjects for this job into a single dict keyed by
    # ntis_project_id (eliminates the per-outcome N+1 lookup).
    project_rows = db.execute(
        select(NtisProject).where(NtisProject.job_id == job_uuid)
    ).scalars().all()
    if not project_rows:
        return 0
    project_by_ntis_id: dict[str, NtisProject] = {
        p.ntis_project_id: p for p in project_rows if p.ntis_project_id
    }
    first_project = project_rows[0]

    rows: list[dict] = []
    seen_paper_ids: set[uuid.UUID] = set()

    for ntis_paper in collector.search_papers(
        keyword=keyword,
        max_results=_MAX_NTIS_PAPER_RESULTS,
        year_start=year_start,
        year_end=year_end,
    ):
        ntis_title = ntis_paper.get("ResultTitle") or ""
        paper_id = title_norm_index.get(_norm_title(ntis_title))
        if not paper_id or paper_id in seen_paper_ids:
            continue
        ntis_proj_id = ntis_paper.get("ProjectID")
        project = (
            project_by_ntis_id.get(str(ntis_proj_id)) if ntis_proj_id else None
        ) or first_project
        rows.append({
            "id": uuid.uuid4(),
            "job_id": job_uuid,
            "ntis_project_id": project.id,
            "matched_paper_id": paper_id,
            "matched_author_id": None,
            "match_type": "paper_outcome_direct",
            "similarity_score": 1.0,
            "match_details": {
                "ntis_result_id": ntis_paper.get("ResultID"),
                "ntis_title": ntis_title,
                "sci_type": ntis_paper.get("SciType"),
                "journal": ntis_paper.get("JournalName"),
                "issn": ntis_paper.get("IssnNumber"),
            },
        })
        seen_paper_ids.add(paper_id)

    if rows:
        from sqlalchemy import insert
        db.execute(insert(ComparativeResult), rows)

    logger.info("NTIS paper direct matches: %d for job %s", len(rows), job_uuid)
    return len(rows)


def _norm_title(title: str) -> str:
    """Normalise title the same way as processing/normalizer.py."""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t
