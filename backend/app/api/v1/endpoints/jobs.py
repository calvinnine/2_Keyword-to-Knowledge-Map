import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import AnalysisJob, JobStatus
from app.nlp.query_parser import HeuristicQueryParser
from app.nlp.translate import contains_hangul, translate_keyword_to_english
from app.schemas.job import (
    JobCreate,
    JobFromQuery,
    JobListItem,
    JobRead,
    KeywordExpansionRead,
    KeywordExpansionRequest,
    ParsedQueryRead,
)

router = APIRouter()


def _enqueue_pipeline_for_job(db: Session, job: AnalysisJob) -> None:
    """Enqueue the analysis pipeline. Defensive against worker unavailability."""
    try:
        from app.workers.tasks.pipeline import enqueue_pipeline
        task_id = enqueue_pipeline(str(job.id))
        job.celery_task_id = task_id
        db.commit()
        db.refresh(job)
    except Exception as exc:  # pragma: no cover
        job.status = JobStatus.FAILED
        job.error_message = f"enqueue: {exc}"
        db.commit()
        db.refresh(job)


@router.post(
    "/expand-keywords",
    response_model=KeywordExpansionRead,
    summary="Preview expanded search terms without creating a job",
)
def expand_keywords_preview(payload: KeywordExpansionRequest) -> KeywordExpansionRead:
    """Translate (if Korean) and expand a keyword into candidate search terms.

    Three layers:
      1. LLM translate+expand (Groq llama-3.3-70b) — single call, domain-aware
      2. OpenAlex concept autocomplete — validates each LLM candidate actually
         exists in the academic index (catches hallucinations / outdated translations)
      3. Wikipedia interlanguage link (ko → en) — for Hangul input only, adds
         the curated English title as an extra candidate when LLM may not know
         the latest term.
    """
    from app.nlp.query_expansion import translate_and_expand
    from app.nlp.grounding import (
        validate_terms_bulk,
        validate_term_with_oa,
        lookup_wiki_langlink,
    )
    from app.schemas.job import TermInfo as TermInfoSchema

    original = payload.keyword
    result = translate_and_expand(original)
    terms: list[str] = list(result["search_terms"])

    # Layer 2: OA validation for every LLM-proposed term (parallel)
    oa_meta = validate_terms_bulk(terms)
    term_info: dict[str, TermInfoSchema] = {
        t: TermInfoSchema(
            oa_works_count=v.get("oa_works_count"),
            source="llm",
        )
        for t, v in oa_meta.items()
    }

    # Layer 3: Wikipedia ko→en for Korean input. Adds bonus candidate.
    if contains_hangul(original):
        wiki_eng = lookup_wiki_langlink(original)
        if wiki_eng:
            # Skip if LLM already proposed an equivalent (case-insensitive)
            existing_lower = {t.lower() for t in terms}
            if wiki_eng.lower() not in existing_lower:
                terms.append(wiki_eng)
                # Validate the wiki term against OA too
                wiki_oa = validate_term_with_oa(wiki_eng)
                term_info[wiki_eng] = TermInfoSchema(
                    oa_works_count=wiki_oa.get("oa_works_count") if wiki_oa else None,
                    source="wikipedia",
                )

    return KeywordExpansionRead(
        original_keyword=original,
        translated_keyword=result["translated"],
        search_terms=terms,
        term_info=term_info,
    )


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> AnalysisJob:
    """Create an analysis job and enqueue the pipeline asynchronously."""
    from app.nlp.query_expansion import translate_and_expand

    # Determine search terms: prefer caller-supplied (pre-confirmed by user),
    # otherwise call the combined translate+expand LLM.
    original_keyword = payload.keyword
    params: dict = {}

    if payload.search_terms and len(payload.search_terms) > 0:
        # User already confirmed terms via /expand-keywords. Use the first
        # term as the primary `keyword` for downstream metadata.
        search_terms = payload.search_terms
        keyword = search_terms[0]
        if contains_hangul(original_keyword):
            params["original_keyword"] = original_keyword
            params["translated_from"] = "ko"
    else:
        # Inline expansion (e.g. API called without UI confirmation step)
        result = translate_and_expand(original_keyword)
        search_terms = result["search_terms"]
        keyword = (
            result["translated"] or search_terms[0] if search_terms else original_keyword
        )
        if result["translated"]:
            params["original_keyword"] = original_keyword
            params["translated_from"] = "ko"

    params["search_terms"] = search_terms

    job = AnalysisJob(
        keyword=keyword,
        max_papers=payload.max_papers,
        year_start=payload.year_start,
        year_end=payload.year_end,
        publication_types=payload.publication_types,
        publication_scope=payload.publication_scope,
        params=params or None,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_pipeline_for_job(db, job)
    return job


@router.post(
    "/parse-query",
    response_model=ParsedQueryRead,
    summary="Preview natural-language → keyword parsing without creating a job",
)
def parse_query(payload: JobFromQuery) -> ParsedQueryRead:
    """Useful for client-side UIs to show the user what keyword will be used
    before they confirm submission of a job.
    """
    parsed = HeuristicQueryParser().parse(payload.query)
    if not parsed.keyword:
        raise HTTPException(
            status_code=422,
            detail="Could not extract a keyword from the query",
        )
    keyword = parsed.keyword
    if contains_hangul(keyword):
        translated = translate_keyword_to_english(keyword)
        if translated and translated != keyword:
            keyword = translated
    return ParsedQueryRead(
        keyword=keyword,
        intent=parsed.intent,
        year_start=parsed.year_start,
        year_end=parsed.year_end,
        raw_query=parsed.raw_query,
    )


@router.post(
    "/from-query",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job from a natural-language question (e.g. \"quantum computing 분야에서 누가 잘해?\")",
)
def create_job_from_query(
    payload: JobFromQuery,
    db: Session = Depends(get_db),
) -> AnalysisJob:
    """Translates an NL query → keyword + intent, then runs the same pipeline.

    The analysis core remains keyword-based. The original NL text and the
    detected intent are preserved on `AnalysisJob.params` so downstream views
    can highlight the relevant graph (author / paper / keyword).
    """
    from app.nlp.query_expansion import translate_and_expand

    parsed = HeuristicQueryParser().parse(payload.query)
    if not parsed.keyword:
        raise HTTPException(
            status_code=422,
            detail="Could not extract a keyword from the query",
        )

    extra_params = parsed.to_params()
    original_keyword = parsed.keyword

    # Two paths:
    #   1) Caller supplied pre-confirmed search_terms (via UI preview step).
    #      Use first term as primary `keyword`, skip LLM expansion.
    #   2) No search_terms → run translate+expand on the parsed keyword so
    #      the natural-language path matches the keyword-input path.
    if payload.search_terms and len(payload.search_terms) > 0:
        search_terms = payload.search_terms
        keyword = search_terms[0]
        if contains_hangul(original_keyword):
            extra_params["original_keyword"] = original_keyword
            extra_params["translated_from"] = "ko"
    else:
        result = translate_and_expand(original_keyword)
        search_terms = result["search_terms"]
        keyword = (
            result["translated"] or (search_terms[0] if search_terms else original_keyword)
        )
        if result["translated"]:
            extra_params["original_keyword"] = original_keyword
            extra_params["translated_from"] = "ko"

    extra_params["search_terms"] = search_terms

    job = AnalysisJob(
        keyword=keyword,
        max_papers=payload.max_papers or 20_000,
        year_start=payload.year_start if payload.year_start is not None else parsed.year_start,
        year_end=payload.year_end if payload.year_end is not None else parsed.year_end,
        publication_types=payload.publication_types,
        publication_scope=payload.publication_scope,
        params=extra_params,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_pipeline_for_job(db, job)
    return job


@router.get("", response_model=list[JobListItem])
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: JobStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> list[AnalysisJob]:
    stmt = select(AnalysisJob).order_by(AnalysisJob.created_at.desc())
    if status_filter:
        stmt = stmt.where(AnalysisJob.status == status_filter)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=409, detail=f"Job already {job.status.value}")

    if job.celery_task_id:
        try:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass  # best-effort

    job.status = JobStatus.CANCELLED
    db.commit()
    db.refresh(job)
    return job
