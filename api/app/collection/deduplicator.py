"""Duplicate detection for ingested signals."""

from enum import Enum
from uuid import UUID

from app.collection.settings import CollectionSettings
from app.repositories.signal import SignalRepository


class DuplicateReason(str, Enum):
    EXTERNAL_ID = "duplicate_external_id"
    URL = "duplicate_url"
    CONTENT_HASH = "duplicate_content_hash"


class DuplicateDetector:
    """Checks PostgreSQL for existing signals before insert."""

    def __init__(
        self,
        signal_repo: SignalRepository,
        settings: CollectionSettings | None = None,
    ) -> None:
        self._signals = signal_repo
        self._settings = settings or CollectionSettings()

    async def check(
        self,
        *,
        source_id: UUID,
        external_id: str,
        url: str,
        content_hash: str,
    ) -> DuplicateReason | None:
        if await self._signals.exists_by_source_and_external_id(source_id, external_id):
            return DuplicateReason.EXTERNAL_ID

        if self._settings.dedup_by_url and await self._signals.exists_by_url(url):
            return DuplicateReason.URL

        if (
            self._settings.dedup_by_content_hash
            and await self._signals.exists_by_source_and_content_hash(source_id, content_hash)
        ):
            return DuplicateReason.CONTENT_HASH

        return None
