"""Comparative analysis: match NTIS projects against K2KM graph results.

Three match strategies (applied in order, each generating independent rows):

1. keyword_overlap   — Jaccard similarity between NTIS project keywords and
                       paper keywords. Score = |intersection| / |union|.
2. author_name       — NTIS researcher names matched against K2KM author display
                       names. Exact (normalised) name match → score 1.0.
3. institution_name  — NTIS performing_org matched against K2KM author
                       affiliations (substring / token match).

A ComparativeResult row is written per (ntis_project, matched_entity) pair
that passes the minimum threshold.
"""

import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ntis import NtisProject, ComparativeResult
from app.models.paper import Paper, PaperKeyword, PaperAuthor
from app.models.author import Author, AuthorAffiliation
from app.models.keyword import Keyword

logger = logging.getLogger(__name__)

_MIN_KEYWORD_JACCARD = 0.10   # ≥10% overlap to record a keyword match
_MIN_AUTHOR_SCORE = 1.0       # exact name match only
_MIN_INST_SCORE = 0.5         # partial token overlap threshold


def run_comparative_analysis(db: Session, job_id: uuid.UUID) -> int:
    """Match all NTIS projects for *job_id* against K2KM entities.

    Returns the total number of ComparativeResult rows inserted.
    """
    projects = db.execute(
        select(NtisProject).where(NtisProject.job_id == job_id)
    ).scalars().all()

    if not projects:
        logger.info("No NTIS projects for job %s; skipping comparative analysis", job_id)
        return 0

    # Pre-load K2KM entities for this job
    papers = db.execute(
        select(Paper).where(Paper.job_id == job_id)
    ).scalars().all()

    paper_keywords = _load_paper_keywords(db, [p.id for p in papers])
    paper_authors = _load_paper_authors(db, [p.id for p in papers])
    authors = {a.id: a for a in db.execute(select(Author)).scalars().all()}
    author_affiliations = _load_author_affiliations(db, list(authors.keys()))

    inserted = 0
    for project in projects:
        inserted += _match_keywords(db, job_id, project, papers, paper_keywords)
        inserted += _match_authors(db, job_id, project, paper_authors, authors)
        inserted += _match_institutions(db, job_id, project, authors, author_affiliations)

    logger.info(
        "Comparative analysis for job %s: %d NTIS projects → %d matches",
        job_id, len(projects), inserted,
    )
    return inserted


# ---------------------------------------------------------------------------
# Match strategy: keyword overlap
# ---------------------------------------------------------------------------

def _match_keywords(
    db: Session,
    job_id: uuid.UUID,
    project: NtisProject,
    papers: list[Paper],
    paper_keywords: dict[uuid.UUID, set[str]],
) -> int:
    ntis_kws = {_norm(k) for k in (project.keywords or []) if k}
    if not ntis_kws:
        return 0

    inserted = 0
    for paper in papers:
        paper_kws = paper_keywords.get(paper.id, set())
        if not paper_kws:
            continue
        intersection = ntis_kws & paper_kws
        union = ntis_kws | paper_kws
        jaccard = len(intersection) / len(union) if union else 0.0
        if jaccard < _MIN_KEYWORD_JACCARD:
            continue
        db.add(ComparativeResult(
            id=uuid.uuid4(),
            job_id=job_id,
            ntis_project_id=project.id,
            matched_paper_id=paper.id,
            match_type="keyword_overlap",
            similarity_score=jaccard,
            match_details={"shared_keywords": sorted(intersection), "jaccard": jaccard},
        ))
        inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Match strategy: author name
# ---------------------------------------------------------------------------

def _match_authors(
    db: Session,
    job_id: uuid.UUID,
    project: NtisProject,
    paper_authors: dict[uuid.UUID, list[uuid.UUID]],  # paper_id → [author_id]
    authors: dict[uuid.UUID, Author],
) -> int:
    ntis_researchers = [_norm(r.get("name", "")) for r in (project.researchers or []) if r.get("name")]
    if not ntis_researchers:
        return 0

    # Collect unique author IDs appearing in this job's papers
    job_author_ids: set[uuid.UUID] = set()
    for aid_list in paper_authors.values():
        job_author_ids.update(aid_list)

    inserted = 0
    matched_authors: set[uuid.UUID] = set()  # avoid duplicate rows per author
    for author_id in job_author_ids:
        author = authors.get(author_id)
        if not author or author_id in matched_authors:
            continue
        display = _norm(author.name or "")
        if not display:
            continue
        if display in ntis_researchers:
            db.add(ComparativeResult(
                id=uuid.uuid4(),
                job_id=job_id,
                ntis_project_id=project.id,
                matched_author_id=author_id,
                match_type="author_name",
                similarity_score=1.0,
                match_details={"matched_name": author.name},
            ))
            matched_authors.add(author_id)
            inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Match strategy: institution name
# ---------------------------------------------------------------------------

def _match_institutions(
    db: Session,
    job_id: uuid.UUID,
    project: NtisProject,
    authors: dict[uuid.UUID, Author],
    author_affiliations: dict[uuid.UUID, list[str]],  # author_id → [raw affiliation strings]
) -> int:
    performing_org = project.performing_org
    if not performing_org:
        return 0

    ntis_tokens = _tokenise(performing_org)
    if not ntis_tokens:
        return 0

    inserted = 0
    matched_authors: set[uuid.UUID] = set()
    for author_id, affiliations in author_affiliations.items():
        if author_id in matched_authors:
            continue
        best_score = 0.0
        best_affiliation = ""
        for affil in affiliations:
            affil_tokens = _tokenise(affil)
            if not affil_tokens:
                continue
            overlap = len(ntis_tokens & affil_tokens) / len(ntis_tokens | affil_tokens)
            if overlap > best_score:
                best_score = overlap
                best_affiliation = affil
        if best_score >= _MIN_INST_SCORE:
            db.add(ComparativeResult(
                id=uuid.uuid4(),
                job_id=job_id,
                ntis_project_id=project.id,
                matched_author_id=author_id,
                match_type="institution_name",
                similarity_score=best_score,
                match_details={
                    "ntis_org": performing_org,
                    "matched_affiliation": best_affiliation,
                    "token_jaccard": best_score,
                },
            ))
            matched_authors.add(author_id)
            inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_paper_keywords(db: Session, paper_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[str]]:
    if not paper_ids:
        return {}
    rows = db.execute(
        select(PaperKeyword.paper_id, Keyword.normalized)
        .join(Keyword, Keyword.id == PaperKeyword.keyword_id)
        .where(PaperKeyword.paper_id.in_(paper_ids))
    ).all()
    result: dict[uuid.UUID, set[str]] = {}
    for paper_id, kw_norm in rows:
        result.setdefault(paper_id, set()).add(_norm(kw_norm or ""))
    return result


def _load_paper_authors(db: Session, paper_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not paper_ids:
        return {}
    rows = db.execute(
        select(PaperAuthor.paper_id, PaperAuthor.author_id)
        .where(PaperAuthor.paper_id.in_(paper_ids))
    ).all()
    result: dict[uuid.UUID, list[uuid.UUID]] = {}
    for paper_id, author_id in rows:
        result.setdefault(paper_id, []).append(author_id)
    return result


def _load_author_affiliations(
    db: Session, author_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    if not author_ids:
        return {}
    rows = db.execute(
        select(AuthorAffiliation.author_id, AuthorAffiliation.raw_affiliation)
        .where(AuthorAffiliation.author_id.in_(author_ids))
    ).all()
    result: dict[uuid.UUID, list[str]] = {}
    for author_id, raw_affil in rows:
        if raw_affil:
            result.setdefault(author_id, []).append(raw_affil)
    return result


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _tokenise(s: str) -> set[str]:
    """Split on whitespace and punctuation; filter stop-words and short tokens."""
    _STOP = {"of", "the", "and", "in", "for", "at", "de", "대학교", "주식회사"}
    tokens = re.split(r"[\s,.()\[\]{}]+", s.lower())
    return {t for t in tokens if len(t) > 1 and t not in _STOP}
