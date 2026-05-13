"""Domestic R&D Relevance scoring.

Computed **after** the NTIS overlay has run (requires ComparativeResult rows).

Score formula  [0, 1]:
  base       = 0.20  if author.primary_country_code == "KR"  else 0.0
  name_match = 0.50  if author has ≥1 author_name comparative match
  inst_match = 0.30  if author has ≥1 institution_name comparative match
               (capped so base + name + inst ≤ 1.0)

Multiple project matches accumulate a bonus up to +0.20 (beyond the first):
  bonus = min(0.20, 0.05 * (match_count - 1))

Final = min(1.0, base + name_match + inst_match + bonus)

Role update:
  "Strategic Connector" is added when:
      global_scholarly_impact ≥ 0.60 AND domestic_rnd_relevance ≥ 0.60
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.metrics import AuthorMetrics
from app.models.ntis import ComparativeResult

logger = logging.getLogger(__name__)

_ROLE_STRATEGIC = "Strategic Connector"

# Score weights
_W_KR_BASE = 0.20
_W_NAME_MATCH = 0.50
_W_INST_MATCH = 0.30
_W_EXTRA_MATCH = 0.05   # per additional project match beyond the first
_CAP_EXTRA = 0.20


def compute_domestic_scores(db: Session, job_id: uuid.UUID) -> int:
    """Compute domestic_rnd_relevance for every AuthorMetrics row in this job.

    Also appends "Strategic Connector" to role_labels when thresholds are met.

    Returns the number of AuthorMetrics rows updated.
    """
    # Load all AuthorMetrics for this job
    metrics_rows: list[AuthorMetrics] = db.execute(
        select(AuthorMetrics).where(AuthorMetrics.job_id == job_id)
    ).scalars().all()

    if not metrics_rows:
        logger.info("No AuthorMetrics found for job %s; skipping domestic scoring", job_id)
        return 0

    author_ids = [m.author_id for m in metrics_rows]

    # Load author country codes
    authors: dict[uuid.UUID, Author] = {
        a.id: a
        for a in db.execute(
            select(Author).where(Author.id.in_(author_ids))
        ).scalars().all()
    }

    # Load comparative results for this job — author-matched rows
    comp_rows = db.execute(
        select(
            ComparativeResult.matched_author_id,
            ComparativeResult.match_type,
        ).where(
            ComparativeResult.job_id == job_id,
            ComparativeResult.matched_author_id.isnot(None),
        )
    ).all()

    # Aggregate per author
    name_match_count: dict[uuid.UUID, int] = {}
    inst_match_count: dict[uuid.UUID, int] = {}
    for author_id, match_type in comp_rows:
        if match_type == "author_name":
            name_match_count[author_id] = name_match_count.get(author_id, 0) + 1
        elif match_type == "institution_name":
            inst_match_count[author_id] = inst_match_count.get(author_id, 0) + 1

    updated = 0
    for m in metrics_rows:
        author = authors.get(m.author_id)
        is_kr = (author is not None and author.primary_country_code == "KR")

        n_names = name_match_count.get(m.author_id, 0)
        n_insts = inst_match_count.get(m.author_id, 0)
        total_matches = n_names + n_insts

        base = _W_KR_BASE if is_kr else 0.0
        name_score = _W_NAME_MATCH if n_names > 0 else 0.0
        inst_score = _W_INST_MATCH if n_insts > 0 else 0.0
        bonus = min(_CAP_EXTRA, _W_EXTRA_MATCH * max(0, total_matches - 1))

        relevance = min(1.0, base + name_score + inst_score + bonus)
        m.domestic_rnd_relevance = round(relevance, 4)

        # Strategic Connector: high global impact AND high domestic R&D relevance
        gsi = m.global_scholarly_impact or 0.0
        if gsi >= 0.60 and relevance >= 0.60:
            labels: list = list(m.role_labels or [])
            if _ROLE_STRATEGIC not in labels:
                labels.append(_ROLE_STRATEGIC)
                m.role_labels = labels

        updated += 1

    logger.info(
        "Domestic R&D relevance computed for job %s: %d authors updated", job_id, updated
    )
    return updated
