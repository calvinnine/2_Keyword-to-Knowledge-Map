import abc
from collections.abc import Generator
from typing import Any


class BaseCollector(abc.ABC):
    """Abstract base for all external data collectors."""

    @abc.abstractmethod
    def search(
        self,
        keyword: str,
        max_results: int,
        year_start: int | None = None,
        year_end: int | None = None,
        **kwargs: Any,
    ) -> Generator[dict, None, None]:
        """Yield raw paper dicts up to max_results."""
        ...

    @abc.abstractmethod
    def get_paper(self, source_id: str) -> dict | None:
        """Fetch a single paper by its source-native ID."""
        ...
