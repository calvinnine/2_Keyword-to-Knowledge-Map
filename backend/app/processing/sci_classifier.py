"""WoS classification for papers via ISSN lookup.

Matches Paper.venue_issn against the wos_journals table (populated from
Clarivate's Master Journal List CSV). Papers whose journal is not in the
registry — or whose venue_issn is NULL — receive sci_classification = NULL.

Classification values: SCIE | SSCI | AHCI | ESCI

When a journal belongs to multiple WoS indexes, priority order is applied:
  SSCI > SCIE > AHCI > ESCI
(Social-science journals are often indexed in both SSCI and SCIE; SSCI wins.)
"""

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.paper import Paper

logger = logging.getLogger(__name__)

_INDEX_PRIORITY = {"SSCI": 0, "SCIE": 1, "AHCI": 2, "ESCI": 3}


def classify_papers(db: Session, job_id: uuid.UUID) -> int:
    """Classify papers for *job_id* using WoS ISSN lookup.

    Updates Paper.sci_classification in place; caller must commit.
    Returns the number of papers updated.
    """
    papers = db.execute(
        select(Paper).where(
            Paper.job_id == job_id,
            Paper.sci_classification.is_(None),
            Paper.venue_issn.is_not(None),
        )
    ).scalars().all()

    if not papers:
        logger.info("SCI classification for job %s: no papers with venue_issn to classify", job_id)
        return 0

    issns = {p.venue_issn for p in papers}

    # Fetch all matching rows from wos_journals in one query
    rows = db.execute(
        text(
            "SELECT issn_l, wos_index FROM wos_journals WHERE issn_l = ANY(:issns)"
        ),
        {"issns": list(issns)},
    ).all()

    # Build issn → best_wos_index mapping (lowest priority number wins)
    issn_map: dict[str, str] = {}
    for issn_l, wos_index in rows:
        if wos_index not in _INDEX_PRIORITY:
            continue
        current = issn_map.get(issn_l)
        if current is None or _INDEX_PRIORITY[wos_index] < _INDEX_PRIORITY[current]:
            issn_map[issn_l] = wos_index

    updated = 0
    for paper in papers:
        label = issn_map.get(paper.venue_issn)
        if label is not None:
            paper.sci_classification = label
            updated += 1

    logger.info(
        "SCI classification for job %s: %d / %d papers classified "
        "(ISSN lookup, %d unique ISSNs matched)",
        job_id, updated, len(papers), len(issn_map),
    )
    return updated
