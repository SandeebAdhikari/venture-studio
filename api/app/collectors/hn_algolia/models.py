"""Hacker News Algolia collector models and configuration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

DEFAULT_PAIN_KEYWORDS: tuple[str, ...] = (
    "frustrated",
    "frustrating",
    "annoying",
    "hate",
    "broken",
    "bug",
    "issue",
    "problem",
    "struggle",
    "struggling",
    "wish",
    "alternative",
    "too expensive",
    "overpriced",
    "pricing",
    "doesn't work",
    "doesnt work",
    "can't",
    "cant",
    "unable",
    "painful",
    "nightmare",
    "terrible",
    "worst",
    "missing feature",
    "need a tool",
    "someone should build",
    "no way to",
    "complaint",
    "disappointed",
    "unusable",
)


class HnAlgoliaCollectorSettings(BaseModel):
    """Runtime settings for the HN Algolia collector."""

    base_url: str = "https://hn.algolia.com/api/v1"
    user_agent: str = "venture-studio-hn-collector/1.0 (contact: collector@local)"
    request_timeout_sec: float = 15.0
    rate_limit_interval_sec: float = 1.0
    max_retries: int = 3
    retry_backoff_sec: float = 2.0
    collector_version: str = "hn_algolia_collector_v1"


class HnAlgoliaSourceConfig(BaseModel):
    """Per-source HN Algolia search configuration stored in sources.config."""

    query: str
    tags: str = "story"
    hits_per_page: int = Field(default=20, ge=1, le=100)
    max_pages: int = Field(default=3, ge=1, le=10)
    keywords: list[str] = Field(default_factory=list)
    min_keyword_matches: int = Field(default=1, ge=1)
    min_points: int = Field(default=0, ge=0)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned

    @field_validator("tags")
    @classmethod
    def strip_tags(cls, value: str) -> str:
        cleaned = value.strip()
        return cleaned or "story"

    def resolved_keywords(self) -> list[str]:
        if self.keywords:
            return [keyword.strip().lower() for keyword in self.keywords if keyword.strip()]
        return list(DEFAULT_PAIN_KEYWORDS)


class HnAlgoliaStory(BaseModel):
    """Normalized Hacker News story from Algolia search."""

    external_id: str
    object_id: str
    title: str
    body: str
    author: str | None
    url: str
    hn_url: str
    published_at: datetime | None
    points: int = 0
    num_comments: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> HnAlgoliaStory | None:
        object_id = hit.get("objectID")
        if not object_id:
            return None

        title = (hit.get("title") or "").strip()
        story_text = (hit.get("story_text") or "").strip()
        body = story_text or title
        if not body:
            return None

        author = hit.get("author")
        if author in {"[deleted]", "[removed]"}:
            author = None

        external_url = (hit.get("url") or "").strip()
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
        url = external_url or hn_url

        created = hit.get("created_at_i")
        published_at = (
            datetime.fromtimestamp(int(created), tz=UTC) if created is not None else None
        )

        return cls(
            external_id=f"hn_{object_id}",
            object_id=str(object_id),
            title=title,
            body=body,
            author=author,
            url=url,
            hn_url=hn_url,
            published_at=published_at,
            points=int(hit.get("points") or 0),
            num_comments=int(hit.get("num_comments") or 0),
            raw=hit,
        )


class HnAlgoliaFetchStats(BaseModel):
    pages_fetched: int = 0
    hits_fetched: int = 0
    keyword_matches: int = 0
    duplicates_skipped: int = 0
    keyword_filtered: int = 0
    points_filtered: int = 0


class HnAlgoliaCollectionStats(BaseModel):
    fetch_stats: HnAlgoliaFetchStats = Field(default_factory=HnAlgoliaFetchStats)
    total_candidates: int = 0
    total_returned: int = 0


class HnAlgoliaSearchResult(BaseModel):
    stories: list[HnAlgoliaStory] = Field(default_factory=list)
    pages_fetched: int = 0
