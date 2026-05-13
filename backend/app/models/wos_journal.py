"""WoS Master Journal List registry.

Populated by importing Clarivate's publicly downloadable MJL CSV
(https://mjl.clarivate.com/). Updated periodically via the
`python -m app.commands.import_wos_journals` CLI command.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WosJournal(Base):
    """One row per linking-ISSN in the Clarivate Master Journal List.

    wos_index values: SCIE | SSCI | AHCI | ESCI
    A journal may appear in multiple indexes — store one row per (issn_l, wos_index) pair.
    """

    __tablename__ = "wos_journals"

    # Linking ISSN (issn_l) — used as the join key against Paper.venue_issn
    issn_l: Mapped[str] = mapped_column(String(20), primary_key=True)

    # WoS index this row belongs to
    wos_index: Mapped[str] = mapped_column(String(10), primary_key=True)  # SCIE | SSCI | AHCI | ESCI

    # Optional metadata from MJL CSV
    journal_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # When this row was last imported/updated
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
