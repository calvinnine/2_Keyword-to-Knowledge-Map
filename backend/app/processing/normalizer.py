"""Canonical normalization utilities for papers, authors, and keywords."""

import re
import unicodedata


def normalize_doi(raw: str | None) -> str | None:
    """Return a lowercased, stripped DOI or None."""
    if not raw:
        return None
    doi = raw.strip().lower()
    # Strip leading URL prefix
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi or None


def normalize_title(raw: str | None) -> str | None:
    """Return a normalized title fingerprint for fallback deduplication.

    Lowercased, unicode-normalized, punctuation and whitespace stripped.
    """
    if not raw:
        return None
    text = unicodedata.normalize("NFKD", raw)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_keyword(raw: str | None) -> str | None:
    """Return a lowercased, stripped keyword for deduplication."""
    if not raw:
        return None
    return raw.strip().lower() or None


def normalize_author_name(raw: str | None) -> str | None:
    if not raw:
        return None
    name = unicodedata.normalize("NFKC", raw).strip()
    # Collapse internal whitespace
    name = re.sub(r"\s+", " ", name)
    if not name:
        return None
    # Reject institution-style names:
    # 1) Contains "/" (e.g. "경남대학교/컴퓨터공학부")
    if "/" in name:
        return None
    # 2) Too many words — real person names rarely exceed 6 tokens
    if len(name.split()) > 6:
        return None
    # 3) Ends with common institution suffixes (Korean universities/departments)
    _INSTITUTION_SUFFIXES = ("대학교", "대학원", "연구원", "연구소", "학부", "학과", "센터", "院", "所")
    if name.endswith(_INSTITUTION_SUFFIXES):
        return None
    return name


def decode_inverted_abstract(inverted: dict | None) -> str | None:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted:
        return None
    # inverted = {word: [pos1, pos2, ...], ...}
    positions: dict[int, str] = {}
    for word, pos_list in inverted.items():
        for pos in pos_list:
            positions[pos] = word
    if not positions:
        return None
    return " ".join(positions[i] for i in sorted(positions))
