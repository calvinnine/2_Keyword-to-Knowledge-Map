"""Affiliation and country extraction.

Country is derived from affiliation metadata (institution location) only.
Nationality of an author is never inferred or stored.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ISO 3166-1 alpha-2 codes commonly embedded in affiliation strings or API responses
_COUNTRY_CODE_PATTERN = re.compile(r"\b([A-Z]{2})\b")


def extract_country(affiliation_data: dict | None) -> tuple[str | None, str | None]:
    """Extract (country_code, country_name) from an OpenAlex or S2 affiliation dict.

    Returns (None, None) if the information is unavailable or ambiguous.
    Never infers nationality.
    """
    if not affiliation_data:
        return None, None

    # OpenAlex institution structure: {"country_code": "US", "display_name": "...", ...}
    country_code = affiliation_data.get("country_code")
    country_name = affiliation_data.get("country") or affiliation_data.get("country_name")

    if isinstance(country_code, str):
        country_code = country_code.strip().upper() or None
    else:
        country_code = None

    if isinstance(country_name, str):
        country_name = country_name.strip() or None
    else:
        country_name = None

    return country_code, country_name


def extract_openalex_affiliation(authorship: dict) -> list[dict]:
    """Parse an OpenAlex authorship entry into a list of affiliation records.

    Each record contains: institution_openalex_id, institution_name,
    country_code, country_name, ror_id.
    """
    institutions = authorship.get("institutions") or []
    result = []
    for inst in institutions:
        if not isinstance(inst, dict):
            continue
        cc, cn = extract_country(inst)
        result.append(
            {
                "institution_openalex_id": inst.get("id"),
                "institution_name": inst.get("display_name"),
                "ror_id": inst.get("ror"),
                "country_code": cc,
                "country_name": cn,
                "raw_affiliation": authorship.get("raw_affiliation_strings", [""])[0]
                if authorship.get("raw_affiliation_strings")
                else None,
            }
        )
    return result


def extract_s2_affiliation(author_entry: dict) -> dict:
    """Parse a Semantic Scholar author entry into an affiliation record."""
    affiliations = author_entry.get("affiliations") or []
    raw = affiliations[0] if affiliations else None
    return {
        "institution_name": raw,
        "country_code": None,
        "country_name": None,
        "raw_affiliation": raw,
    }
