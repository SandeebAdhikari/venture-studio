"""Complaint collection service — ingests raw data as deduplicated signals."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.collection.deduplicator import DuplicateDetector
from app.collection.filters import CollectionFilter
from app.collection.normalizer import TextNormalizer
from app.collection.schemas import (
    CollectionItemResult,
    CollectionResult,
    RawComplaintBatch,
    RawComplaintInput,
)
from app.collection.settings import CollectionSettings
from app.exceptions import NotFoundError, ValidationError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.repositories.signal import SignalCreateData

logger = get_logger(__name__)


class ComplaintCollectionService:
    """Ingests raw complaint data into PostgreSQL as pending signals."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: CollectionSettings | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or CollectionSettings()
        self._normalizer = TextNormalizer(version=self._settings.normalizer_version)
        self._filter = CollectionFilter(self._settings)
        self._deduplicator = DuplicateDetector(repos.signals, self._settings)

    async def ingest(self, source_id: UUID, item: RawComplaintInput) -> CollectionItemResult:
        result = await self.ingest_batch(RawComplaintBatch(source_id=source_id, items=[item]))
        return result.items[0]

    async def ingest_batch(self, batch: RawComplaintBatch) -> CollectionResult:
        source = await self._repos.sources.get_by_id(batch.source_id)
        if source is None:
            raise NotFoundError("source", batch.source_id)
        if not source.enabled:
            raise ValidationError(f"Source '{batch.source_id}' is disabled")

        collection_result = CollectionResult(source_id=batch.source_id)

        for item in batch.items:
            item_result = await self._process_item(batch.source_id, source.name, item)
            collection_result.add_item(item_result)

        if collection_result.inserted > 0:
            await self._repos.sources.record_collection_success(batch.source_id)

        logger.info(
            "Collection batch complete",
            extra={
                "source_id": str(batch.source_id),
                "inserted": collection_result.inserted,
                "duplicates": collection_result.duplicates,
                "skipped": collection_result.skipped,
            },
        )
        return collection_result

    async def _process_item(
        self,
        source_id: UUID,
        source_name: str,
        item: RawComplaintInput,
    ) -> CollectionItemResult:
        normalized = self._normalizer.normalize(title=item.title, body=item.body)

        skip_reason = self._filter.rejection_reason(normalized, url=item.url)
        if skip_reason is not None:
            return CollectionItemResult(
                external_id=item.external_id,
                status="skipped",
                reason=skip_reason,
            )

        duplicate_reason = await self._deduplicator.check(
            source_id=source_id,
            external_id=item.external_id,
            url=item.url.strip(),
            content_hash=normalized.content_hash,
        )
        if duplicate_reason is not None:
            return CollectionItemResult(
                external_id=item.external_id,
                status="duplicate",
                reason=duplicate_reason.value,
            )

        metadata = self._build_metadata(
            source_name=source_name,
            incoming_metadata=item.metadata,
            normalized=normalized,
        )

        signal = await self._repos.signals.insert_signal(
            SignalCreateData(
                source_id=source_id,
                external_id=item.external_id,
                url=item.url.strip(),
                title=normalized.title,
                body=normalized.body,
                author=item.author,
                published_at=item.published_at,
                metadata=metadata,
                content_hash=normalized.content_hash,
            )
        )

        if signal is None:
            return CollectionItemResult(
                external_id=item.external_id,
                status="duplicate",
                reason="duplicate_external_id",
            )

        return CollectionItemResult(
            external_id=item.external_id,
            status="inserted",
            signal_id=signal.id,
        )

    def _build_metadata(
        self,
        *,
        source_name: str,
        incoming_metadata: dict[str, Any],
        normalized,
    ) -> dict[str, Any]:
        return {
            **incoming_metadata,
            "collection": {
                "source_name": source_name,
                "collected_at": datetime.now(UTC).isoformat(),
                "normalizer_version": normalized.normalizer_version,
                "content_hash": normalized.content_hash,
                "combined_text_length": len(normalized.combined_text),
            },
        }
