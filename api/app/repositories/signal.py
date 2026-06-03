"""Signal repository for collection and deduplication."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SignalProcessingStatus
from app.db.models.signal import Signal
from app.repositories.base import BaseRepository


class SignalCreateData:
    """Internal DTO for signal insertion."""

    __slots__ = (
        "source_id",
        "external_id",
        "url",
        "title",
        "body",
        "author",
        "published_at",
        "metadata",
        "content_hash",
    )

    def __init__(
        self,
        *,
        source_id: UUID,
        external_id: str,
        url: str,
        title: str | None,
        body: str,
        author: str | None,
        published_at: datetime | None,
        metadata: dict,
        content_hash: str,
    ) -> None:
        self.source_id = source_id
        self.external_id = external_id
        self.url = url
        self.title = title
        self.body = body
        self.author = author
        self.published_at = published_at
        self.metadata = metadata
        self.content_hash = content_hash


class SignalRepository(BaseRepository[Signal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Signal)

    async def exists_by_source_and_external_id(self, source_id: UUID, external_id: str) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(Signal)
            .where(Signal.source_id == source_id, Signal.external_id == external_id)
        )
        return int(result.scalar_one()) > 0

    async def exists_by_url(self, url: str) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(Signal).where(Signal.url == url)
        )
        return int(result.scalar_one()) > 0

    async def exists_by_source_and_content_hash(self, source_id: UUID, content_hash: str) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(Signal)
            .where(Signal.source_id == source_id, Signal.content_hash == content_hash)
        )
        return int(result.scalar_one()) > 0

    async def get_by_source_and_external_id(
        self,
        source_id: UUID,
        external_id: str,
    ) -> Signal | None:
        result = await self.session.execute(
            select(Signal).where(
                Signal.source_id == source_id,
                Signal.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def insert_signal(self, data: SignalCreateData) -> Signal | None:
        """Insert a signal, returning None if a unique constraint conflict occurs."""
        stmt = (
            insert(Signal)
            .values(
                source_id=data.source_id,
                external_id=data.external_id,
                url=data.url,
                title=data.title,
                body=data.body,
                author=data.author,
                published_at=data.published_at,
                signal_metadata=data.metadata,
                content_hash=data.content_hash,
                processing_status=SignalProcessingStatus.PENDING.value,
            )
            .on_conflict_do_nothing(index_elements=["source_id", "external_id"])
            .returning(Signal.id)
        )
        result = await self.session.execute(stmt)
        signal_id = result.scalar_one_or_none()
        if signal_id is None:
            return None

        return await self.get_by_id(signal_id)

    async def list_pending(self, *, limit: int = 50) -> list[Signal]:
        result = await self.session.execute(
            select(Signal)
            .where(Signal.processing_status == SignalProcessingStatus.PENDING.value)
            .order_by(Signal.collected_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def set_processing_status(
        self,
        signal: Signal,
        status: SignalProcessingStatus,
        *,
        skip_reason: str | None = None,
    ) -> Signal:
        signal.processing_status = status.value
        signal.skip_reason = skip_reason
        await self.session.flush()
        await self.session.refresh(signal)
        return signal
