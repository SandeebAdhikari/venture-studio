"""RSS feed REST endpoints."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AppSettings, Services
from app.api.pagination import Pagination
from app.schemas.pagination import PaginatedResponse
from app.schemas.rss_feed import RssFeedCreate, RssFeedRead

router = APIRouter(prefix="/rss-feeds", tags=["rss-feeds"])


@router.post(
    "",
    response_model=RssFeedRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register an RSS feed for collection",
    responses={status.HTTP_409_CONFLICT: {"description": "Feed URL already registered"}},
)
async def create_rss_feed(data: RssFeedCreate, services: Services) -> RssFeedRead:
    return await services.rss_feeds.create_feed(data)


@router.get(
    "",
    response_model=PaginatedResponse[RssFeedRead],
    summary="List configured RSS feeds",
)
async def list_rss_feeds(
    services: Services,
    pagination: Pagination,
) -> PaginatedResponse[RssFeedRead]:
    return await services.rss_feeds.list_feeds(pagination)


@router.delete(
    "/{feed_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an RSS feed and linked source",
    description="Hard-delete an RSS feed. Disabled in production.",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Deletion disabled in production"},
        status.HTTP_404_NOT_FOUND: {"description": "RSS feed not found"},
    },
)
async def delete_rss_feed(feed_id: UUID, services: Services, settings: AppSettings) -> None:
    await services.rss_feeds.delete_feed(feed_id, settings)
