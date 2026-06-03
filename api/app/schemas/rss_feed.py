"""RSS feed persistence schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, HttpUrl

from app.db.enums import RssFeedCategory
from app.schemas.common import ORMModel, UUIDSchema


class RssFeedCreate(ORMModel):
    name: str = Field(max_length=100)
    feed_url: HttpUrl
    category: RssFeedCategory = RssFeedCategory.GENERAL
    enabled: bool = True
    polling_interval_sec: int = Field(default=3600, ge=60)
    entry_limit: int = Field(default=30, ge=1, le=100)


class RssFeedRead(RssFeedCreate, UUIDSchema):
    source_id: UUID
    last_polled_at: datetime | None = None
    last_error: str | None = None
