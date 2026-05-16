"""Citation count enrichment — tiered policy with multi-source cross-walk.

Policy (decided 2026-05-16, see WORK_PROGRESS.md):

  Headline `citation_count` =
      MAX(S2 value, OpenAlex value if sanity-check passes)
      else NULL

  Identifier strategy: each paper has up to 3 candidate IDs.  We try them in
  order until S2 returns a hit.
      1) DOI         (journal/conference DOI from OpenAlex)
      2) ARXIV       (preprint, from OpenAlex `ids.arxiv` — same paper, different DOI)
      3) (future: CorpusId)

  Sanity check on OpenAlex `counts_by_year`:
      Calculate the citation fraction attributed to years BEFORE the paper's
      `publication_year`.  We allow legitimate "preprint era" citations (typically
      a small fraction), but reject catastrophic contamination such as the
      W4294558607 case where 80%+ of citations were attributed to years 5-7
      before publication.  Threshold: > 10% pre-publication → reject the OA value.

  Citation breakdown (decision 3C):
      Using S2's `citations.publicationTypes`, count citing papers by venue type.
      - journal: JournalArticle | Conference | Review
      - preprint: Preprint | no type info (S2 leaves arXiv entries un-typed)
      Limitation: S2 paginates the citations list; for very-high-citation papers
      we only see the first page (~100-1000).  Sum may therefore underestimate
      total when `citation_by_journal + citation_by_preprint < citation_count`.

  See "기술 부채 / 정밀도 업그레이드 대기" in WORK_PROGRESS for the upgrades we
  deferred (INTERSECTION strategy, per-citing-paper validation).
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
from app.models.raw import RawPayload

logger = logging.getLogger(__name__)

# Two-pass batching: S2 enforces tighter rate limits on heavy fields like
# `citations.publicationTypes`. Pass 1 is large batch with cheap fields;
# Pass 2 is smaller batch with citation list for breakdown.
_BATCH_SIZE_LIGHT = 500
_BATCH_SIZE_HEAVY = 25

_S2_FIELDS_LIGHT = "externalIds,citationCount,influentialCitationCount"
_S2_FIELDS_HEAVY = "externalIds,citations.publicationTypes"

# Limit the breakdown lookup to top-N papers by citation_count.
# This avoids spending rate-limit budget on long-tail low-citation papers.
_BREAKDOWN_TOP_N = 50

# Sanity-check threshold: max fraction of citations allowed in years before
# the paper's publication_year. Higher → catastrophic OA contamination.
_OA_PREPUB_FRACTION_LIMIT = 0.10

# S2 publication types we classify as "journal-style" (peer-reviewed).
_JOURNAL_TYPES = {"JournalArticle", "Conference", "Review"}
_PREPRINT_TYPES = {"Preprint"}


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _candidate_s2_ids(paper: Paper, oa_payload: dict | None) -> list[str]:
    """Return ordered S2 identifier candidates for this paper.

    Order matters: DOI first (most specific), then arXiv DOI, then arXiv ID,
    so we land on the journal version if it exists, else the preprint."""
    ids: list[str] = []
    if paper.doi:
        ids.append(f"DOI:{paper.doi}")
    if oa_payload:
        oa_ids = oa_payload.get("ids") or {}
        arxiv_url = oa_ids.get("arxiv")
        if arxiv_url:
            # OpenAlex stores arxiv as URL: https://arxiv.org/abs/2207.02547
            arxiv_id = arxiv_url.rstrip("/").split("/")[-1]
            if arxiv_id:
                ids.append(f"DOI:10.48550/arXiv.{arxiv_id}")
                ids.append(f"ARXIV:{arxiv_id}")
    # Also try the stored arxiv_id on the paper itself
    if paper.arxiv_id:
        arxiv_id = paper.arxiv_id.rstrip("/").split("/")[-1]
        candidate_doi = f"DOI:10.48550/arXiv.{arxiv_id}"
        if candidate_doi not in ids:
            ids.append(candidate_doi)
        candidate_arxiv = f"ARXIV:{arxiv_id}"
        if candidate_arxiv not in ids:
            ids.append(candidate_arxiv)
    return ids


def _oa_count_passes_sanity(payload: dict, publication_year: int | None) -> bool:
    """Return True if OpenAlex `counts_by_year` distribution looks plausible.

    Rejects cases where a large share of citations are attributed to years
    BEFORE the paper's publication date (almost always cross-work contamination).
    """
    if publication_year is None:
        # Without a publication_year we can't run the check; default to accepting
        # — the worst case is keeping a slightly wrong number from OA.
        return True
    counts_by_year = payload.get("counts_by_year") or []
    if not counts_by_year:
        return True
    total = sum((c.get("cited_by_count") or 0) for c in counts_by_year)
    if total == 0:
        return True
    prepub = sum(
        (c.get("cited_by_count") or 0)
        for c in counts_by_year
        if (c.get("year") or 0) < publication_year
    )
    return (prepub / total) <= _OA_PREPUB_FRACTION_LIMIT


def _classify_citations(citations: list[dict]) -> tuple[int, int]:
    """Count citing papers as (journal_like, preprint_like) by publicationTypes."""
    journal = 0
    preprint = 0
    for c in citations or []:
        types = c.get("publicationTypes") or []
        if any(t in _JOURNAL_TYPES for t in types):
            journal += 1
        elif any(t in _PREPRINT_TYPES for t in types):
            preprint += 1
        elif not types:
            # S2 frequently leaves arXiv/CorpusID-only entries un-typed.
            # Best heuristic: treat as preprint.
            preprint += 1
        # else: types like Dataset/Editorial/etc → leave out of both buckets
    return journal, preprint


def enrich_citations_from_s2(db: Session, job_id: uuid.UUID) -> dict[str, int]:
    """Apply tiered citation enrichment to every paper in `job_id`.

    Updates Paper rows in place with: citation_count, citation_source,
    influential_citation_count, citation_by_journal, citation_by_preprint.
    """
    papers = db.execute(
        select(Paper).where(Paper.job_id == job_id)
    ).scalars().all()
    if not papers:
        return {"s2": 0, "openalex": 0, "null": 0, "total": 0}

    # ------------------------------------------------------------------
    # Phase 1: build OA raw-payload lookup by openalex_id for sanity-check
    # ------------------------------------------------------------------
    oa_payload_by_openalex_id: dict[str, dict] = {}
    raws = db.execute(
        select(RawPayload).where(
            RawPayload.job_id == job_id, RawPayload.source == "openalex"
        )
    ).scalars()
    for raw in raws:
        oa_id = (raw.payload or {}).get("id")
        if oa_id:
            oa_payload_by_openalex_id[oa_id] = raw.payload

    # ------------------------------------------------------------------
    # Phase 2: S2 multi-ID lookup
    # ------------------------------------------------------------------
    # Build full set of S2 IDs to try, with paper→id mapping for reverse lookup.
    paper_to_ids: dict[uuid.UUID, list[str]] = {}
    id_to_paper: dict[str, Paper] = {}
    all_ids: list[str] = []
    for p in papers:
        oa_payload = oa_payload_by_openalex_id.get(p.openalex_id or "")
        candidates = _candidate_s2_ids(p, oa_payload)
        if not candidates:
            continue
        paper_to_ids[p.id] = candidates
        for cid in candidates:
            id_to_paper.setdefault(cid, p)
            all_ids.append(cid)

    # Dedup all_ids preserving order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for x in all_ids:
        if x not in seen:
            seen.add(x)
            unique_ids.append(x)

    logger.info(
        "S2 enrichment: %d papers, %d candidate IDs", len(papers), len(unique_ids)
    )

    def _match_paper(entry: dict) -> Paper | None:
        ext = entry.get("externalIds") or {}
        doi = ext.get("DOI")
        arxiv = ext.get("ArXiv")
        if doi:
            key = f"DOI:{doi.lower()}"
            if key in id_to_paper:
                return id_to_paper[key]
            key = f"DOI:{doi}"
            if key in id_to_paper:
                return id_to_paper[key]
        if arxiv:
            if f"ARXIV:{arxiv}" in id_to_paper:
                return id_to_paper[f"ARXIV:{arxiv}"]
            if f"DOI:10.48550/arXiv.{arxiv}" in id_to_paper:
                return id_to_paper[f"DOI:10.48550/arXiv.{arxiv}"]
        return None

    # ----- Pass 1 (light): citationCount + influentialCitationCount -----
    s2_result_by_paper: dict[uuid.UUID, dict] = {}
    try:
        with SemanticScholarCollector() as collector:
            for chunk in _chunks(unique_ids, _BATCH_SIZE_LIGHT):
                results = collector.get_papers_bulk_with_fields(
                    chunk, _S2_FIELDS_LIGHT
                )
                for entry in results:
                    if not entry or not isinstance(entry, dict):
                        continue
                    paper = _match_paper(entry)
                    if not paper:
                        continue
                    s2_count = entry.get("citationCount")
                    if s2_count is None:
                        continue
                    prev = s2_result_by_paper.get(paper.id)
                    if prev is None or (prev.get("count") or 0) < s2_count:
                        s2_result_by_paper[paper.id] = {
                            "count": int(s2_count),
                            "influential": entry.get("influentialCitationCount"),
                            "journal": None,
                            "preprint": None,
                        }
    except Exception:
        logger.exception("S2 enrichment pass1: batch lookup failed for job %s", job_id)

    logger.info(
        "S2 enrichment pass1 done: %d papers got S2 citation data",
        len(s2_result_by_paper),
    )

    # ----- Pass 2 (heavy): citations.publicationTypes for top-N -----
    # Only fetch breakdown for papers with the highest S2 counts; the long tail
    # rarely justifies the rate-limit cost.
    top_paper_ids = sorted(
        s2_result_by_paper.keys(),
        key=lambda pid: s2_result_by_paper[pid]["count"] or 0,
        reverse=True,
    )[:_BREAKDOWN_TOP_N]
    top_lookup_ids: list[str] = []
    for pid in top_paper_ids:
        for cid in paper_to_ids.get(pid, []):
            top_lookup_ids.append(cid)
            break  # one ID per paper is enough for pass 2

    if top_lookup_ids:
        try:
            with SemanticScholarCollector() as collector:
                for chunk in _chunks(top_lookup_ids, _BATCH_SIZE_HEAVY):
                    results = collector.get_papers_bulk_with_fields(
                        chunk, _S2_FIELDS_HEAVY
                    )
                    for entry in results:
                        if not entry or not isinstance(entry, dict):
                            continue
                        paper = _match_paper(entry)
                        if not paper:
                            continue
                        journal, preprint = _classify_citations(
                            entry.get("citations") or []
                        )
                        if paper.id in s2_result_by_paper:
                            s2_result_by_paper[paper.id]["journal"] = journal
                            s2_result_by_paper[paper.id]["preprint"] = preprint
        except Exception:
            logger.exception(
                "S2 enrichment pass2: breakdown lookup failed for job %s", job_id
            )

    # ------------------------------------------------------------------
    # Phase 3: apply tiered policy per paper
    # ------------------------------------------------------------------
    counts = {"s2": 0, "openalex": 0, "null": 0, "total": len(papers)}
    for p in papers:
        s2 = s2_result_by_paper.get(p.id)
        oa_payload = oa_payload_by_openalex_id.get(p.openalex_id or "")
        oa_count: int | None = None
        if oa_payload is not None:
            raw = oa_payload.get("cited_by_count")
            if raw is not None and _oa_count_passes_sanity(oa_payload, p.publication_year):
                oa_count = int(raw)

        s2_count = s2["count"] if s2 else None

        # MAX strategy: pick the larger of the two; tag source accordingly.
        chosen: int | None = None
        source: str | None = None
        if s2_count is not None and oa_count is not None:
            if s2_count >= oa_count:
                chosen, source = s2_count, "s2"
            else:
                chosen, source = oa_count, "openalex"
        elif s2_count is not None:
            chosen, source = s2_count, "s2"
        elif oa_count is not None:
            chosen, source = oa_count, "openalex"

        p.citation_count = chosen
        p.citation_source = source

        # Influential + breakdown only available from S2.
        if s2 is not None:
            p.influential_citation_count = s2.get("influential")
            p.citation_by_journal = s2.get("journal")
            p.citation_by_preprint = s2.get("preprint")
        else:
            p.influential_citation_count = None
            p.citation_by_journal = None
            p.citation_by_preprint = None

        if source == "s2":
            counts["s2"] += 1
        elif source == "openalex":
            counts["openalex"] += 1
        else:
            counts["null"] += 1

    db.commit()
    logger.info(
        "S2 enrichment done for job %s: s2=%d, oa_fallback=%d, null=%d, total=%d",
        job_id, counts["s2"], counts["openalex"], counts["null"], counts["total"],
    )
    return counts
