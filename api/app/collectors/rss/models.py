"""RSS collector models and configuration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RssCollectorSettings(BaseModel):
    user_agent: str = "venture-studio-rss-collector/1.0 (contact: collector@local)"
    request_timeout_sec: float = 15.0
    rate_limit_interval_sec: float = 1.0
    max_retries: int = 3
    retry_backoff_sec: float = 2.0
    collector_version: str = "rss_collector_v1"
    force_poll: bool = False


class RssSourceConfig(BaseModel):
    url: str
    category: str = "general"
    limit: int = Field(default=30, ge=1, le=100)
    polling_interval_sec: int = Field(default=3600, ge=60)
    feed_id: str | None = None
    feed_name: str | None = None

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()

    @classmethod
    def from_source_config(cls, config: dict[str, Any]) -> RssSourceConfig:
        return cls.model_validate(config)


class RssFeedEntry(BaseModel):
    external_id: str
    url: str
    title: str | None = None
    body: str
    author: str | None = None
    published_at: datetime | None = None
    feed_title: str | None = None
    entry_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_feedparser_entry(cls, entry: Any, *, feed_title: str | None) -> RssFeedEntry | None:
        link = (getattr(entry, "link", None) or "").strip()
        if not link:
            return None

        title = (getattr(entry, "title", None) or "").strip() or None
        summary = (getattr(entry, "summary", None) or getattr(entry, "description", None) or "").strip()
        body = summary or title or ""
        if not body:
            return None

        guid = getattr(entry, "id", None) or getattr(entry, "guid", None) or link
        external_id = str(guid)[:255]

        author = getattr(entry, "author", None)
        published_at = None
        published = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if published is not None:
            try:
                published_at = datetime(*published[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                published_at = None

        return cls(
            external_id=external_id,
            url=link,
            title=title,
            body=body,
            author=author,
            published_at=published_at,
            feed_title=feed_title,
            entry_id=str(getattr(entry, "id", "") or "") or None,
        )


class RssFetchStats(BaseModel):
    entries_fetched: int = 0
    entries_returned: int = 0
    duplicates_skipped: int = 0
    polling_skipped: bool = False
