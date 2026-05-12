"""SCI/SSCI/ESCI classification for papers.

Uses OpenAlex fields_of_study (already stored on Paper) to infer whether a
journal paper would be indexed in SCIE (natural sciences), SSCI (social
sciences), or ESCI (emerging sources). Non-journal papers are left NULL.

This is a heuristic approximation; the authoritative classification is
Clarivate's Web of Science, which requires a paid API key.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper

logger = logging.getLogger(__name__)

# OpenAlex level-0 concept names that map to SSCI
_SSCI_CONCEPTS: frozenset[str] = frozenset({
    "sociology",
    "political science",
    "economics",
    "psychology",
    "business",
    "law",
    "linguistics",
    "management",
    "anthropology",
    "communication",
    "education",
    "social science",
    "public administration",
    "demography",
})

# OpenAlex level-0 concept names that map to SCIE
_SCIE_CONCEPTS: frozenset[str] = frozenset({
    "computer science",
    "mathematics",
    "physics",
    "chemistry",
    "biology",
    "medicine",
    "engineering",
    "materials science",
    "geology",
    "geography",
    "environmental science",
    "astronomy",
    "biochemistry",
    "neuroscience",
    "pharmacology",
    "immunology",
    "ecology",
    "bioinformatics",
    "quantum mechanics",
})

# Arts & Humanities Citation Index
_AHCI_CONCEPTS: frozenset[str] = frozenset({
    "philosophy",
    "art",
    "history",
    "literature",
    "musicology",
    "theology",
    "classics",
})


def _classify_from_fields(fields_of_study: list[dict] | None, venue_type: str | None) -> str | None:
    """Infer SCI classification from stored fields_of_study metadata.

    Returns one of: "SCIE", "SSCI", "AHCI", "ESCI", or None.
    """
    if venue_type and venue_type not in ("journal", "other", None):
        # Conferences, preprints, books are not WoS-indexed under SCI/SSCI
        return None

    if not fields_of_study:
        # No field data → can't classify
        return None

    # Gather level-0 concept names (top-level disciplines)
    top_concepts = [
        f.get("display_name", "").lower()
        for f in fields_of_study
        if isinstance(f, dict) and f.get("level", 99) == 0
    ]

    # Also include level-1 if no level-0 is available (some records omit level-0)
    if not top_concepts:
        top_concepts = [
            f.get("display_name", "").lower()
            for f in fields_of_study
            if isinstance(f, dict) and f.get("level", 99) == 1
        ]

    if not top_concepts:
        return None

    ssci_hit = any(c in _SSCI_CONCEPTS for c in top_concepts)
    scie_hit = any(c in _SCIE_CONCEPTS for c in top_concepts)
    ahci_hit = any(c in _AHCI_CONCEPTS for c in top_concepts)

    if scie_hit and not ssci_hit:
        return "SCIE"
    if ssci_hit and not scie_hit:
        return "SSCI"
    if scie_hit and ssci_hit:
        # Interdisciplinary — use score to break the tie
        scores: dict[str, float] = {}
        for f in fields_of_study:
            if not isinstance(f, dict):
                continue
            name = f.get("display_name", "").lower()
            score = float(f.get("score", 0))
            if name in _SSCI_CONCEPTS or name in _SCIE_CONCEPTS:
                scores[name] = score
        ssci_score = sum(scores[c] for c in top_concepts if c in _SSCI_CONCEPTS)
        scie_score = sum(scores[c] for c in top_concepts if c in _SCIE_CONCEPTS)
        return "SSCI" if ssci_score > scie_score else "SCIE"
    if ahci_hit:
        return "AHCI"

    # Journal with known venue_type but unmatched concepts → ESCI bucket
    if venue_type == "journal":
        return "ESCI"

    return None


def classify_papers(db: Session, job_id: uuid.UUID) -> int:
    """Classify papers for *job_id* that have no sci_classification yet.

    Updates Paper.sci_classification in place; caller must commit.
    Returns the number of papers updated.
    """
    papers = db.execute(
        select(Paper).where(
            Paper.job_id == job_id,
            Paper.sci_classification.is_(None),
        )
    ).scalars().all()

    updated = 0
    for paper in papers:
        label = _classify_from_fields(paper.fields_of_study, paper.venue_type)
        if label is not None:
            paper.sci_classification = label
            updated += 1

    logger.info(
        "SCI classification for job %s: %d / %d papers classified",
        job_id, updated, len(papers),
    )
    return updated
