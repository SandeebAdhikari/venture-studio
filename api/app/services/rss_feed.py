"""RSS feed management service."""

from uuid import UUID

from app.config import Settings
from app.db.enums import SourceType
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories import RepositoryContainer
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.rss_feed import RssFeedCreate, RssFeedRead
from app.schemas.source import SourceCreate, SourceUpdate


class RssFeedService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def create_feed(self, data: RssFeedCreate) -> RssFeedRead:
        feed_url = str(data.feed_url)
        existing = await self._repos.rss_feeds.get_by_feed_url(feed_url)
        if existing is not None:
            raise ConflictError(f"RSS feed URL '{feed_url}' is already registered")

        source = await self._repos.sources.create(
            SourceCreate(
                name=data.name,
                source_type=SourceType.RSS,
                config={
                    "url": feed_url,
                    "category": data.category.value,
                    "limit": data.entry_limit,
                    "polling_interval_sec": data.polling_interval_sec,
                },
                enabled=data.enabled,
            )
        )
        entity = await self._repos.rss_feeds.create(data, source_id=source.id)
        source.config = {
            **source.config,
            "feed_id": str(entity.id),
            "feed_name": entity.name,
        }
        await self._repos.sources.update(
            source,
            SourceUpdate(config=source.config),
        )
        return RssFeedRead.model_validate(entity)

    async def list_feeds(self, pagination: PaginationParams) -> PaginatedResponse[RssFeedRead]:
        items = await self._repos.rss_feeds.list_feeds(
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.rss_feeds.count_feeds()
        return PaginatedResponse[RssFeedRead](
            items=[RssFeedRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def delete_feed(self, feed_id: UUID, settings: Settings) -> None:
        if settings.is_production:
            raise ForbiddenError("RSS feed deletion is disabled in production")
        entity = await self._repos.rss_feeds.get_by_id(feed_id)
        if entity is None:
            raise NotFoundError("rss_feed", feed_id)

        source = await self._repos.sources.get_by_id(entity.source_id)
        await self._repos.rss_feeds.delete(entity)
        if source is not None:
            await self._repos.sources.delete(source)
