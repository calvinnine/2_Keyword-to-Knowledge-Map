"""DOI-first deduplication with title-normalization fallback.

Strategy:
1. If a canonical DOI is present → use DOI as the unique key.
2. If DOI is missing → use normalized title fingerprint.
3. Within a single job, maintain an in-memory seen set for fast lookup.
   DB-level UNIQUE constraints on `papers.doi` and a partial unique index
   on `papers.title_normalized WHERE doi IS NULL` enforce global uniqueness.
"""

import logging
from dataclasses import dataclass, field

from app.processing.normalizer import normalize_doi, normalize_title

logger = logging.getLogger(__name__)


@dataclass
class PaperDeduplicator:
    """Stateful deduplicator for a single processing run.

    Tracks seen DOIs and title fingerprints so that within-batch duplicates
    are handled before any DB insert is attempted.
    """

    _seen_dois: set[str] = field(default_factory=set, init=False)
    _seen_titles: set[str] = field(default_factory=set, init=False)

    def is_duplicate(self, doi: str | None, title_normalized: str | None) -> bool:
        """Return True if this paper has already been seen in this run."""
        if doi:
            if doi in self._seen_dois:
                return True
        elif title_normalized:
            if title_normalized in self._seen_titles:
                return True
        return False

    def register(self, doi: str | None, title_normalized: str | None) -> None:
        """Mark this paper as seen."""
        if doi:
            self._seen_dois.add(doi)
        if title_normalized:
            self._seen_titles.add(title_normalized)

    def check_and_register(self, doi: str | None, title_normalized: str | None) -> bool:
        """Return True if duplicate; otherwise register and return False."""
        if self.is_duplicate(doi, title_normalized):
            return True
        self.register(doi, title_normalized)
        return False

    @property
    def seen_count(self) -> int:
        return len(self._seen_dois) + len(self._seen_titles)
