"""Reddit collector models and configuration."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

DEFAULT_SUBREDDITS: tuple[str, ...] = (
    "entrepreneur",
    "smallbusiness",
    "startups",
    "SaaS",
    "construction",
    "healthcare",
    "legaltech",
)

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


class RedditContentKind(str, Enum):
    POST = "post"
    COMMENT = "comment"


class RedditSourceConfig(BaseModel):
    """Per-source Reddit collection configuration stored in sources.config."""

    subreddit: str | None = None
    subreddits: list[str] = Field(default_factory=list)
    sort: Literal["new", "hot", "top", "rising"] = "new"
    limit: int = Field(default=25, ge=1, le=100)
    time_filter: Literal["hour", "day", "week", "month", "year", "all"] = "day"
    include_comments: bool = True
    comment_limit: int = Field(default=20, ge=1, le=100)
    keywords: list[str] = Field(default_factory=list)
    min_keyword_matches: int = Field(default=1, ge=1)

    @field_validator("subreddit")
    @classmethod
    def strip_subreddit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("subreddits")
    @classmethod
    def strip_subreddits(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    def resolved_subreddits(self) -> list[str]:
        if self.subreddits:
            return self.subreddits
        if self.subreddit:
            return [self.subreddit]
        return list(DEFAULT_SUBREDDITS)

    def resolved_keywords(self) -> list[str]:
        if self.keywords:
            return [keyword.strip().lower() for keyword in self.keywords if keyword.strip()]
        return list(DEFAULT_PAIN_KEYWORDS)


class RedditCollectorSettings(BaseModel):
    """Runtime settings for the Reddit collector."""

    user_agent: str = "venture-studio-collector/1.0 (contact: collector@local)"
    base_url: str = "https://www.reddit.com"
    request_timeout_sec: float = 15.0
    rate_limit_interval_sec: float = 1.0
    max_retries: int = 3
    retry_backoff_sec: float = 2.0
    collector_version: str = "reddit_collector_v1"


class RedditPost(BaseModel):
    """Normalized Reddit submission."""

    external_id: str
    post_id: str
    subreddit: str
    title: str
    body: str
    author: str | None
    url: str
    permalink: str
    published_at: datetime | None
    score: int = 0
    num_comments: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_listing(cls, data: dict[str, Any]) -> RedditPost | None:
        if data.get("kind") != "t3":
            return None

        payload = data.get("data") or {}
        post_id = payload.get("id")
        if not post_id:
            return None

        title = (payload.get("title") or "").strip()
        selftext = (payload.get("selftext") or "").strip()
        body = selftext or title
        if not body:
            return None

        author = payload.get("author")
        if author in {"[deleted]", "[removed]"}:
            author = None

        permalink = payload.get("permalink") or ""
        full_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink

        created = payload.get("created_utc")
        published_at = (
            datetime.fromtimestamp(float(created), tz=UTC) if created is not None else None
        )

        return cls(
            external_id=payload.get("name") or f"t3_{post_id}",
            post_id=str(post_id),
            subreddit=str(payload.get("subreddit") or ""),
            title=title,
            body=body,
            author=author,
            url=full_url,
            permalink=permalink,
            published_at=published_at,
            score=int(payload.get("score") or 0),
            num_comments=int(payload.get("num_comments") or 0),
            raw=payload,
        )


class RedditComment(BaseModel):
    """Normalized Reddit comment."""

    external_id: str
    comment_id: str
    post_id: str
    subreddit: str
    body: str
    author: str | None
    url: str
    permalink: str
    published_at: datetime | None
    score: int = 0
    parent_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_listing(cls, data: dict[str, Any], *, post: RedditPost) -> RedditComment | None:
        if data.get("kind") != "t1":
            return None

        payload = data.get("data") or {}
        comment_id = payload.get("id")
        body = (payload.get("body") or "").strip()
        if not comment_id or not body:
            return None
        if body in {"[deleted]", "[removed]"}:
            return None

        author = payload.get("author")
        if author in {"[deleted]", "[removed]"}:
            author = None

        permalink = payload.get("permalink") or post.permalink
        full_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink

        created = payload.get("created_utc")
        published_at = (
            datetime.fromtimestamp(float(created), tz=UTC) if created is not None else None
        )

        return cls(
            external_id=payload.get("name") or f"t1_{comment_id}",
            comment_id=str(comment_id),
            post_id=post.post_id,
            subreddit=post.subreddit,
            body=body,
            author=author,
            url=full_url,
            permalink=permalink,
            published_at=published_at,
            score=int(payload.get("score") or 0),
            parent_id=payload.get("parent_id"),
            raw=payload,
        )


class RedditFetchStats(BaseModel):
    subreddit: str
    posts_fetched: int = 0
    comments_fetched: int = 0
    keyword_matches: int = 0
    duplicates_skipped: int = 0
    keyword_filtered: int = 0


class RedditCollectionStats(BaseModel):
    subreddit_stats: list[RedditFetchStats] = Field(default_factory=list)
    total_candidates: int = 0
    total_returned: int = 0
    duplicates_skipped: int = 0
    keyword_filtered: int = 0
