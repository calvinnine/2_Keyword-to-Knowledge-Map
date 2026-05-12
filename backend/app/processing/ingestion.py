"""Ingestion service: converts raw payloads into canonical DB entities.

Handles both OpenAlex and Semantic Scholar payloads.
Maintains deduplication state for the duration of a single job processing run.
"""

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.paper import Paper, PaperSource, PaperAuthor, PaperKeyword, Citation
from app.models.author import Author, AuthorAffiliation
from app.models.institution import Institution
from app.models.keyword import Keyword
from app.models.raw import RawPayload
from app.processing.dedup import PaperDeduplicator
from app.processing.normalizer import (
    normalize_doi,
    normalize_title,
    normalize_keyword,
    normalize_author_name,
    decode_inverted_abstract,
)
from app.processing.affiliation import extract_openalex_affiliation, extract_s2_affiliation

logger = logging.getLogger(__name__)


class IngestionService:
    """Stateful ingestion service for one job run.

    Call process_openalex_payload() or process_s2_payload() for each raw record.
    Commit the session after each batch externally.
    """

    def __init__(self, db: Session, job_id: uuid.UUID) -> None:
        self._db = db
        self._job_id = job_id
        self._dedup = PaperDeduplicator()

        # In-memory caches to avoid per-row DB lookups within a batch
        self._institution_cache: dict[str, uuid.UUID] = {}  # openalex_id → id
        self._author_cache: dict[str, uuid.UUID] = {}       # openalex_id → id
        self._keyword_cache: dict[str, uuid.UUID] = {}      # normalized → id

    # ------------------------------------------------------------------
    # OpenAlex
    # ------------------------------------------------------------------

    def process_openalex_payload(self, raw: RawPayload) -> Paper | None:
        payload = raw.payload
        doi = normalize_doi(payload.get("doi"))
        title_norm = normalize_title(payload.get("title"))

        if self._dedup.check_and_register(doi, title_norm):
            return None

        abstract = decode_inverted_abstract(payload.get("abstract_inverted_index"))
        pub_type = _map_openalex_type(payload.get("type"))

        paper = Paper(
            id=uuid.uuid4(),
            doi=doi,
            title_normalized=title_norm,
            title=payload.get("title"),
            abstract=abstract,
            publication_year=payload.get("publication_year"),
            publication_date=payload.get("publication_date"),
            venue_name=_oa_venue_name(payload),
            venue_type=pub_type,
            citation_count=payload.get("cited_by_count") or 0,
            reference_count=payload.get("referenced_works_count") or 0,
            openalex_id=payload.get("id"),
            is_open_access=payload.get("open_access", {}).get("is_oa") if payload.get("open_access") else None,
            language=payload.get("language"),
            fields_of_study=[c.get("display_name") for c in (payload.get("concepts") or []) if c.get("display_name")],
            job_id=self._job_id,
        )
        # Extract external IDs
        ids = payload.get("ids") or {}
        paper.pubmed_id = ids.get("pmid")
        paper.arxiv_id = ids.get("arxiv")

        self._db.add(paper)

        # Source record
        self._db.add(PaperSource(
            paper_id=paper.id,
            source="openalex",
            source_id=payload.get("id", ""),
            raw_payload_id=raw.id,
        ))

        # Authors + affiliations
        for authorship in (payload.get("authorships") or []):
            author_id = self._get_or_create_author_from_oa(authorship)
            if author_id:
                pos = authorship.get("author_position")
                position_int = {"first": 0, "middle": 1, "last": 2}.get(pos) if pos else None
                self._db.merge(PaperAuthor(
                    paper_id=paper.id,
                    author_id=author_id,
                    author_position=position_int,
                ))
                # Affiliations
                for aff in extract_openalex_affiliation(authorship):
                    inst_id = self._get_or_create_institution(aff) if aff.get("institution_openalex_id") else None
                    self._db.add(AuthorAffiliation(
                        author_id=author_id,
                        institution_id=inst_id,
                        paper_id=paper.id,
                        raw_affiliation=aff.get("raw_affiliation"),
                        country_code=aff.get("country_code"),
                        country_name=aff.get("country_name"),
                    ))

        # Keywords
        keyword_sources = (payload.get("keywords") or []) + (payload.get("concepts") or [])
        for kw_entry in keyword_sources:
            kw_text = kw_entry.get("display_name") if isinstance(kw_entry, dict) else kw_entry
            kw_id = self._get_or_create_keyword(kw_text)
            if kw_id:
                # merge avoids duplicate PK errors
                self._db.merge(PaperKeyword(paper_id=paper.id, keyword_id=kw_id, source="openalex"))

        # Citation stubs (only IDs; full records may not be in our corpus yet)
        for ref_id in (payload.get("referenced_works") or []):
            # Store as (citing=paper, cited=stub) — FK to papers may fail if cited
            # paper is not yet in DB; we defer resolution in a separate pass.
            # Skipped here; resolved in process_citations() after full ingestion.
            pass

        return paper

    # ------------------------------------------------------------------
    # Semantic Scholar
    # ------------------------------------------------------------------

    def process_s2_payload(self, raw: RawPayload) -> Paper | None:
        payload = raw.payload
        ext_ids = payload.get("externalIds") or {}
        doi = normalize_doi(ext_ids.get("DOI"))
        title_norm = normalize_title(payload.get("title"))

        if self._dedup.check_and_register(doi, title_norm):
            return None

        pub_types = payload.get("publicationTypes") or []
        pub_type = _map_s2_type(pub_types)

        paper = Paper(
            id=uuid.uuid4(),
            doi=doi,
            title_normalized=title_norm,
            title=payload.get("title"),
            abstract=payload.get("abstract"),
            publication_year=payload.get("year"),
            publication_date=payload.get("publicationDate"),
            venue_name=_s2_venue_name(payload),
            venue_type=pub_type,
            citation_count=payload.get("citationCount") or 0,
            reference_count=payload.get("referenceCount") or 0,
            semantic_scholar_id=payload.get("paperId"),
            pubmed_id=ext_ids.get("PubMed"),
            arxiv_id=ext_ids.get("ArXiv"),
            is_open_access=payload.get("isOpenAccess"),
            fields_of_study=[f.get("category") for f in (payload.get("s2FieldsOfStudy") or []) if f.get("category")],
            job_id=self._job_id,
        )
        self._db.add(paper)

        self._db.add(PaperSource(
            paper_id=paper.id,
            source="semantic_scholar",
            source_id=payload.get("paperId", ""),
            raw_payload_id=raw.id,
        ))

        for author_entry in (payload.get("authors") or []):
            author_id = self._get_or_create_author_from_s2(author_entry)
            if author_id:
                self._db.merge(PaperAuthor(
                    paper_id=paper.id,
                    author_id=author_id,
                ))
                aff = extract_s2_affiliation(author_entry)
                if aff.get("raw_affiliation"):
                    self._db.add(AuthorAffiliation(
                        author_id=author_id,
                        paper_id=paper.id,
                        raw_affiliation=aff.get("raw_affiliation"),
                        country_code=None,
                        country_name=None,
                    ))

        for fos in (payload.get("fieldsOfStudy") or []):
            kw_id = self._get_or_create_keyword(fos)
            if kw_id:
                self._db.merge(PaperKeyword(paper_id=paper.id, keyword_id=kw_id, source="semantic_scholar"))

        return paper

    # ------------------------------------------------------------------
    # Citation resolution (call after full ingestion)
    # ------------------------------------------------------------------

    def update_author_primary_countries(self) -> int:
        """Aggregate AuthorAffiliation records to set Author.primary_country_code.

        Uses majority-vote over all affiliation records for each author.
        Call once after all ingestion for a job is complete.
        Returns number of authors updated.
        """
        from collections import Counter
        from sqlalchemy import select as sa_select

        authors = self._db.execute(sa_select(Author)).scalars().all()
        updated = 0
        for author in authors:
            aff_rows = self._db.execute(
                sa_select(AuthorAffiliation.country_code, AuthorAffiliation.country_name)
                .where(
                    AuthorAffiliation.author_id == author.id,
                    AuthorAffiliation.country_code.is_not(None),
                )
            ).all()
            if not aff_rows:
                continue
            counter: Counter = Counter(row.country_code for row in aff_rows)
            top_code = counter.most_common(1)[0][0]
            # Grab matching country_name (first occurrence of winning code)
            top_name = next(
                (row.country_name for row in aff_rows if row.country_code == top_code),
                None,
            )
            author.primary_country_code = top_code
            author.primary_country_name = top_name
            updated += 1
        return updated

    def resolve_openalex_citations(self, payload: dict, citing_paper_id: uuid.UUID) -> int:
        """Insert Citation rows for known referenced_works. Returns count inserted."""
        inserted = 0
        for ref_oa_id in (payload.get("referenced_works") or []):
            stmt = select(PaperSource).where(
                PaperSource.source == "openalex",
                PaperSource.source_id == ref_oa_id,
            )
            ps = self._db.execute(stmt).scalar_one_or_none()
            if ps:
                self._db.merge(Citation(
                    citing_paper_id=citing_paper_id,
                    cited_paper_id=ps.paper_id,
                    source="openalex",
                ))
                inserted += 1
        return inserted

    # ------------------------------------------------------------------
    # Private: get-or-create helpers
    # ------------------------------------------------------------------

    def _get_or_create_author_from_oa(self, authorship: dict) -> uuid.UUID | None:
        author_data = authorship.get("author") or {}
        oa_id = author_data.get("id")
        name = normalize_author_name(author_data.get("display_name"))
        if not name:
            return None

        if oa_id and oa_id in self._author_cache:
            return self._author_cache[oa_id]

        if oa_id:
            stmt = select(Author).where(Author.openalex_id == oa_id)
            existing = self._db.execute(stmt).scalar_one_or_none()
            if existing:
                self._author_cache[oa_id] = existing.id
                return existing.id

        author = Author(
            id=uuid.uuid4(),
            name=name,
            openalex_id=oa_id,
            orcid=author_data.get("orcid"),
        )
        self._db.add(author)
        if oa_id:
            self._author_cache[oa_id] = author.id
        return author.id

    def _get_or_create_author_from_s2(self, author_entry: dict) -> uuid.UUID | None:
        s2_id = author_entry.get("authorId")
        name = normalize_author_name(author_entry.get("name"))
        if not name:
            return None

        if s2_id and s2_id in self._author_cache:
            return self._author_cache[s2_id]

        if s2_id:
            stmt = select(Author).where(Author.semantic_scholar_id == s2_id)
            existing = self._db.execute(stmt).scalar_one_or_none()
            if existing:
                self._author_cache[s2_id] = existing.id
                return existing.id

        author = Author(id=uuid.uuid4(), name=name, semantic_scholar_id=s2_id)
        self._db.add(author)
        if s2_id:
            self._author_cache[s2_id] = author.id
        return author.id

    def _get_or_create_institution(self, aff: dict) -> uuid.UUID | None:
        oa_id = aff.get("institution_openalex_id")
        if not oa_id:
            return None
        if oa_id in self._institution_cache:
            return self._institution_cache[oa_id]

        stmt = select(Institution).where(Institution.openalex_id == oa_id)
        existing = self._db.execute(stmt).scalar_one_or_none()
        if existing:
            self._institution_cache[oa_id] = existing.id
            return existing.id

        inst = Institution(
            id=uuid.uuid4(),
            name=aff.get("institution_name") or "Unknown",
            openalex_id=oa_id,
            ror_id=aff.get("ror_id"),
            country_code=aff.get("country_code"),
            country_name=aff.get("country_name"),
        )
        self._db.add(inst)
        self._institution_cache[oa_id] = inst.id
        return inst.id

    def _get_or_create_keyword(self, text: str | None) -> uuid.UUID | None:
        norm = normalize_keyword(text)
        if not norm:
            return None
        if norm in self._keyword_cache:
            return self._keyword_cache[norm]

        stmt = select(Keyword).where(Keyword.normalized == norm)
        existing = self._db.execute(stmt).scalar_one_or_none()
        if existing:
            self._keyword_cache[norm] = existing.id
            return existing.id

        kw = Keyword(id=uuid.uuid4(), normalized=norm, display=(text or norm).strip())
        self._db.add(kw)
        self._keyword_cache[norm] = kw.id
        return kw.id


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _oa_venue_name(payload: dict) -> str | None:
    loc = payload.get("primary_location") or {}
    source = loc.get("source") or {}
    return source.get("display_name")


def _s2_venue_name(payload: dict) -> str | None:
    pv = payload.get("publicationVenue") or {}
    return pv.get("name") or payload.get("venue")


def _map_openalex_type(raw_type: str | None) -> str | None:
    if not raw_type:
        return None
    mapping = {
        "article": "journal",
        "journal-article": "journal",
        "proceedings-article": "conference",
        "preprint": "preprint",
        "book-chapter": "book_chapter",
        "book": "book",
        "dataset": "dataset",
        "dissertation": "dissertation",
        "review": "review",
        "report": "report",
    }
    return mapping.get(raw_type.lower(), "other")


def _map_s2_type(pub_types: list[str]) -> str | None:
    if not pub_types:
        return None
    for t in pub_types:
        lower = t.lower()
        if "journal" in lower:
            return "journal"
        if "conference" in lower:
            return "conference"
        if "review" in lower:
            return "review"
    return "other"
