"""RSS feed repository."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.rss_feed import RssFeed
from app.repositories.base import BaseRepository
from app.schemas.rss_feed import RssFeedCreate


class RssFeedRepository(BaseRepository[RssFeed]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RssFeed)

    async def get_by_feed_url(self, feed_url: str) -> RssFeed | None:
        result = await self.session.execute(select(RssFeed).where(RssFeed.feed_url == feed_url))
        return result.scalar_one_or_none()

    async def get_by_source_id(self, source_id: UUID) -> RssFeed | None:
        result = await self.session.execute(select(RssFeed).where(RssFeed.source_id == source_id))
        return result.scalar_one_or_none()

    async def list_feeds(self, *, limit: int = 50, offset: int = 0) -> list[RssFeed]:
        result = await self.session.execute(
            select(RssFeed).order_by(RssFeed.name).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_feeds(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(RssFeed))
        return int(result or 0)

    async def create(self, data: RssFeedCreate, *, source_id: UUID) -> RssFeed:
        entity = RssFeed(
            name=data.name,
            feed_url=str(data.feed_url),
            category=data.category.value,
            enabled=data.enabled,
            polling_interval_sec=data.polling_interval_sec,
            entry_limit=data.entry_limit,
            source_id=source_id,
        )
        return await self.add(entity)

    async def mark_polled(self, entity: RssFeed) -> RssFeed:
        entity.last_polled_at = datetime.now(UTC)
        entity.last_error = None
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def record_error(self, entity: RssFeed, error: str) -> RssFeed:
        entity.last_error = error
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
