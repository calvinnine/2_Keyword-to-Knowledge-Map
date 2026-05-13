"""Import / refresh the WoS Master Journal List from a Clarivate CSV file.

Usage:
    python -m app.commands.import_wos_journals <path/to/mjl.csv>

How to get the CSV:
    1. Go to https://mjl.clarivate.com/
    2. Click "Download entire collection" (or filter by index first)
    3. Save the CSV file and pass its path to this command.

Expected CSV columns (Clarivate format, as of 2024):
    - "Full Journal Title" or "Journal title"
    - "ISSN" or "Print ISSN"
    - "eISSN" or "E-ISSN"
    - "Coverage" — one or more of: SCIE, SSCI, AHCI, ESCI

The importer is lenient about column name variations and delimiter differences.
It performs an UPSERT so repeated runs are safe and act as a refresh.
"""

import csv
import io
import logging
import sys
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.models.wos_journal import WosJournal

logger = logging.getLogger(__name__)

_VALID_INDEXES = frozenset({"SCIE", "SSCI", "AHCI", "ESCI"})

# Column name aliases (case-insensitive)
_TITLE_COLS = {"full journal title", "journal title", "title"}
_ISSN_COLS = {"issn", "print issn", "issn (print)"}
_EISSN_COLS = {"eissn", "e-issn", "issn (electronic)"}
_COVERAGE_COLS = {"coverage", "wos index", "web of science index", "index"}


def _normalise_issn(raw: str) -> str | None:
    """Return 'XXXX-XXXX' or None."""
    s = raw.strip().replace(" ", "").upper()
    if len(s) == 8 and s.isalnum():
        return f"{s[:4]}-{s[4:]}"
    if len(s) == 9 and s[4] == "-":
        return s
    return None


def _detect_col(headers: list[str], candidates: set[str]) -> str | None:
    for h in headers:
        if h.strip().lower() in candidates:
            return h
    return None


def _parse_indexes(coverage_val: str) -> list[str]:
    """Extract valid WoS index codes from a coverage cell."""
    # Values may be comma/semicolon/space separated, e.g. "SCIE; SSCI"
    parts = coverage_val.replace(";", ",").replace("|", ",").split(",")
    return [p.strip().upper() for p in parts if p.strip().upper() in _VALID_INDEXES]


def import_csv(csv_path: str | Path) -> tuple[int, int]:
    """Parse *csv_path* and upsert into wos_journals.

    Returns (rows_inserted_or_updated, journals_with_no_issn_skipped).
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    raw_bytes = path.read_bytes()
    # Detect encoding: try UTF-8-BOM first, fall back to latin-1
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Could not decode CSV — try converting to UTF-8")

    # Detect delimiter
    sample = text[:4096]
    dialect = csv.Sniffer().sniff(sample, delimiters=",\t|")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []

    col_title = _detect_col(headers, _TITLE_COLS)
    col_issn = _detect_col(headers, _ISSN_COLS)
    col_eissn = _detect_col(headers, _EISSN_COLS)
    col_coverage = _detect_col(headers, _COVERAGE_COLS)

    if col_coverage is None:
        raise ValueError(
            f"Cannot find a coverage/index column. Headers found: {headers}\n"
            "Expected one of: " + ", ".join(sorted(_COVERAGE_COLS))
        )

    records: list[dict] = []
    skipped = 0

    for row in reader:
        title = row.get(col_title, "").strip() if col_title else None
        issn_raw = row.get(col_issn, "").strip() if col_issn else ""
        eissn_raw = row.get(col_eissn, "").strip() if col_eissn else ""
        coverage = row.get(col_coverage, "").strip()

        issn = _normalise_issn(issn_raw) or _normalise_issn(eissn_raw)
        if not issn:
            skipped += 1
            continue

        indexes = _parse_indexes(coverage)
        if not indexes:
            # Row not in any recognised WoS index — skip
            skipped += 1
            continue

        for idx in indexes:
            records.append({
                "issn_l": issn,
                "wos_index": idx,
                "journal_title": title[:500] if title else None,
            })

    if not records:
        logger.warning("No valid records found in %s", path)
        return 0, skipped

    db = SessionLocal()
    try:
        stmt = pg_insert(WosJournal).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["issn_l", "wos_index"],
            set_={
                "journal_title": stmt.excluded.journal_title,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        db.execute(stmt)
        db.commit()
        logger.info("Upserted %d wos_journals rows (%d skipped)", len(records), skipped)
    finally:
        db.close()

    return len(records), skipped


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = sys.argv[1]
    try:
        inserted, skipped = import_csv(csv_path)
        print(f"Done. Upserted {inserted} rows, skipped {skipped} rows.")
    except Exception as exc:
        logger.error("Import failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
