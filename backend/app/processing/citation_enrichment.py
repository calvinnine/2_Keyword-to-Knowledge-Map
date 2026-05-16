"""Citation count enrichment via Semantic Scholar.

Background
----------
OpenAlex was the original source of `citation_count`, but it ships occasional
data-integrity bugs — most visibly: citation counts merged across unrelated
works (paper published 2024, counts attributed back to 2017). For an analysis
platform whose central premise is "show influential papers and their authors,"
unreliable citation counts are a deal-breaker.

Semantic Scholar derives citation counts paper-by-paper from reference-text
parsing, which is more reliable. We use the S2 `/paper/batch` endpoint
(up to 500 papers per request) to verify counts after OpenAlex/S2 ingestion.

Behaviour
---------
- For every paper in the job with a DOI, look it up in S2 by `DOI:<doi>`.
- If S2 returns a `citationCount`, store it on the Paper.
- If S2 doesn't return the paper (no DOI / not indexed / API miss), set
  `citation_count = NULL` so the UI can show "-" instead of misleading data.
- Papers with no DOI at all are skipped (citation_count stays NULL).

Note: this runs AFTER ingestion is fully committed, so it's a separate
SQL `UPDATE` pass — no FK or ordering complications.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors import SemanticScholarCollector
from app.models.paper import Paper

logger = logging.getLogger(__name__)

# S2 /paper/batch supports up to 500 ids per request.
_BATCH_SIZE = 500


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def enrich_citations_from_s2(db: Session, job_id: uuid.UUID) -> dict[str, int]:
    """Verify and update citation_count for every paper in this job via S2.

    Returns a stats dict: {'looked_up': N, 'verified': K, 'missing': M}
      - looked_up: papers with DOI we tried to verify
      - verified: papers S2 returned a count for (count now reliable)
      - missing: papers S2 had no record of (count set to NULL)
    """
    papers = db.execute(
        select(Paper).where(Paper.job_id == job_id, Paper.doi.is_not(None))
    ).scalars().all()

    if not papers:
        logger.info("S2 enrichment: no DOI-bearing papers in job %s", job_id)
        return {"looked_up": 0, "verified": 0, "missing": 0}

    # Build DOI → Paper map. S2 batch accepts "DOI:<doi>" syntax.
    doi_to_paper: dict[str, Paper] = {}
    for p in papers:
        if p.doi:
            doi_to_paper[p.doi] = p

    s2_ids = [f"DOI:{doi}" for doi in doi_to_paper.keys()]
    looked_up = len(s2_ids)
    logger.info("S2 enrichment: looking up %d papers in job %s", looked_up, job_id)

    verified = 0
    seen_dois: set[str] = set()

    try:
        with SemanticScholarCollector() as collector:
            for chunk in _chunks(s2_ids, _BATCH_SIZE):
                results = collector.get_papers_bulk(chunk)
                for entry in results:
                    if not entry or not isinstance(entry, dict):
                        # S2 returns `null` in the array slot for unknown IDs;
                        # we skip those — they remain in `missing`.
                        continue
                    ext = entry.get("externalIds") or {}
                    doi = (ext.get("DOI") or "").lower().strip()
                    if not doi or doi not in doi_to_paper:
                        continue
                    citation_count = entry.get("citationCount")
                    if citation_count is None:
                        continue
                    paper = doi_to_paper[doi]
                    paper.citation_count = int(citation_count)
                    seen_dois.add(doi)
                    verified += 1
    except Exception as exc:  # best-effort — don't fail the job over S2 hiccups
        logger.exception("S2 enrichment failed for job %s: %s", job_id, exc)

    # Papers whose DOI we tried but S2 returned no data → set NULL explicitly,
    # so we don't carry stale (unreliable) OpenAlex counts.
    missing_papers: list[Paper] = []
    for doi, paper in doi_to_paper.items():
        if doi not in seen_dois:
            paper.citation_count = None
            missing_papers.append(paper)

    # Papers without any DOI — also forcibly NULL (OpenAlex value, if any, is suspect).
    no_doi_papers = db.execute(
        select(Paper).where(Paper.job_id == job_id, Paper.doi.is_(None))
    ).scalars().all()
    for p in no_doi_papers:
        p.citation_count = None

    db.commit()

    stats = {
        "looked_up": looked_up,
        "verified": verified,
        "missing": len(missing_papers),
        "no_doi": len(no_doi_papers),
    }
    logger.info(
        "S2 enrichment done for job %s: verified=%d / looked_up=%d, "
        "missing=%d, no_doi=%d",
        job_id, verified, looked_up, stats["missing"], stats["no_doi"],
    )
    return stats
