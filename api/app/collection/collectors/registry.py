"""Source collector registry for the COLLECT pipeline stage."""

from __future__ import annotations

from typing import Protocol

from app.collection.schemas import RawComplaintInput
from app.db.models.source import Source


class SourceCollector(Protocol):
    """Fetches raw complaint items from an external source."""

    async def fetch(self, source: Source) -> list[RawComplaintInput]: ...


_COLLECTORS: dict[str, SourceCollector] = {}


def register_collector(source_type: str, collector: SourceCollector) -> None:
    _COLLECTORS[source_type] = collector


def get_collector(source_type: str) -> SourceCollector | None:
    return _COLLECTORS.get(source_type)


def clear_collectors() -> None:
    _COLLECTORS.clear()
