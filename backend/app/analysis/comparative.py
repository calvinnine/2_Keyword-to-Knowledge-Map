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

from sqlalchemy import select, insert
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

    Performance: all matches are accumulated into a single list and inserted
    via SQLAlchemy Core bulk insert at the end, avoiding the per-row ORM
    overhead of `db.add(ComparativeResult(...))`.
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
    paper_ids = [p.id for p in papers]

    paper_keywords = _load_paper_keywords(db, paper_ids)
    paper_authors = _load_paper_authors(db, paper_ids)

    # Restrict authors to those appearing in this job's papers (was: global)
    job_author_ids: set[uuid.UUID] = set()
    for aid_list in paper_authors.values():
        job_author_ids.update(aid_list)

    if job_author_ids:
        authors = {
            a.id: a
            for a in db.execute(
                select(Author).where(Author.id.in_(job_author_ids))
            ).scalars().all()
        }
    else:
        authors = {}

    author_affiliations = _load_author_affiliations(db, list(authors.keys()))

    # Pre-tokenise author affiliations once (was: per-project, per-author)
    author_affil_token_sets: dict[uuid.UUID, list[tuple[str, set[str]]]] = {
        aid: [(affil, _tokenise(affil)) for affil in affils]
        for aid, affils in author_affiliations.items()
    }

    rows: list[dict] = []
    for project in projects:
        _collect_keyword_matches(rows, job_id, project, papers, paper_keywords)
        _collect_author_matches(rows, job_id, project, job_author_ids, authors)
        _collect_institution_matches(rows, job_id, project, author_affil_token_sets)

    if rows:
        db.execute(insert(ComparativeResult), rows)

    logger.info(
        "Comparative analysis for job %s: %d NTIS projects → %d matches",
        job_id, len(projects), len(rows),
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Match strategy: keyword overlap
# ---------------------------------------------------------------------------

def _collect_keyword_matches(
    rows: list[dict],
    job_id: uuid.UUID,
    project: NtisProject,
    papers: list[Paper],
    paper_keywords: dict[uuid.UUID, set[str]],
) -> None:
    ntis_kws = {_norm(k) for k in (project.keywords or []) if k}
    if not ntis_kws:
        return

    ntis_kws_len = len(ntis_kws)
    for paper in papers:
        paper_kws = paper_keywords.get(paper.id)
        if not paper_kws:
            continue
        # Quick rejection: if there's no intersection at all, skip the
        # union calculation. This is the dominant inner-loop case.
        intersection = ntis_kws & paper_kws
        if not intersection:
            continue
        union_size = ntis_kws_len + len(paper_kws) - len(intersection)
        jaccard = len(intersection) / union_size if union_size else 0.0
        if jaccard < _MIN_KEYWORD_JACCARD:
            continue
        rows.append({
            "id": uuid.uuid4(),
            "job_id": job_id,
            "ntis_project_id": project.id,
            "matched_paper_id": paper.id,
            "matched_author_id": None,
            "match_type": "keyword_overlap",
            "similarity_score": jaccard,
            "match_details": {"shared_keywords": sorted(intersection), "jaccard": jaccard},
        })


# ---------------------------------------------------------------------------
# Match strategy: author name
# ---------------------------------------------------------------------------

def _collect_author_matches(
    rows: list[dict],
    job_id: uuid.UUID,
    project: NtisProject,
    job_author_ids: set[uuid.UUID],
    authors: dict[uuid.UUID, Author],
) -> None:
    ntis_researchers = {
        _norm(r.get("name", ""))
        for r in (project.researchers or [])
        if r.get("name")
    }
    if not ntis_researchers:
        return

    matched_authors: set[uuid.UUID] = set()
    for author_id in job_author_ids:
        if author_id in matched_authors:
            continue
        author = authors.get(author_id)
        if not author:
            continue
        display = _norm(author.name or "")
        if not display:
            continue
        if display in ntis_researchers:
            rows.append({
                "id": uuid.uuid4(),
                "job_id": job_id,
                "ntis_project_id": project.id,
                "matched_paper_id": None,
                "matched_author_id": author_id,
                "match_type": "author_name",
                "similarity_score": 1.0,
                "match_details": {"matched_name": author.name},
            })
            matched_authors.add(author_id)


# ---------------------------------------------------------------------------
# Match strategy: institution name
# ---------------------------------------------------------------------------

def _collect_institution_matches(
    rows: list[dict],
    job_id: uuid.UUID,
    project: NtisProject,
    author_affil_token_sets: dict[uuid.UUID, list[tuple[str, set[str]]]],
) -> None:
    performing_org = project.performing_org
    if not performing_org:
        return

    ntis_tokens = _tokenise(performing_org)
    if not ntis_tokens:
        return

    matched_authors: set[uuid.UUID] = set()
    for author_id, token_pairs in author_affil_token_sets.items():
        if author_id in matched_authors:
            continue
        best_score = 0.0
        best_affiliation = ""
        for affil, affil_tokens in token_pairs:
            if not affil_tokens:
                continue
            inter = len(ntis_tokens & affil_tokens)
            if not inter:
                continue
            union = len(ntis_tokens) + len(affil_tokens) - inter
            overlap = inter / union if union else 0.0
            if overlap > best_score:
                best_score = overlap
                best_affiliation = affil
        if best_score >= _MIN_INST_SCORE:
            rows.append({
                "id": uuid.uuid4(),
                "job_id": job_id,
                "ntis_project_id": project.id,
                "matched_paper_id": None,
                "matched_author_id": author_id,
                "match_type": "institution_name",
                "similarity_score": best_score,
                "match_details": {
                    "ntis_org": performing_org,
                    "matched_affiliation": best_affiliation,
                    "token_jaccard": best_score,
                },
            })
            matched_authors.add(author_id)


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
