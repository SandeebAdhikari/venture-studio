"""Low-level Reddit JSON API client."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import httpx

from app.collectors.reddit.models import RedditCollectorSettings, RedditComment, RedditPost, RedditSourceConfig
from app.logging import get_logger

logger = get_logger(__name__)


class RedditRateLimiter:
    """Distributed-safe rate limiter using Redis with in-process fallback."""

    def __init__(
        self,
        *,
        redis=None,
        min_interval_sec: float = 1.0,
    ) -> None:
        self._redis = redis
        self._min_interval_sec = min_interval_sec
        self._local_last_request: dict[str, float] = {}

    async def wait(self, scope: str) -> None:
        if self._redis is not None:
            await self._wait_redis(scope)
        else:
            await self._wait_local(scope)

    async def _wait_redis(self, scope: str) -> None:
        import time

        key = f"ratelimit:reddit:{scope}"
        while True:
            now = time.time()
            last_raw = await self._redis.get(key)
            if last_raw is None:
                await self._redis.set(key, str(now), ex=max(int(self._min_interval_sec * 2), 2))
                return

            elapsed = now - float(last_raw)
            if elapsed >= self._min_interval_sec:
                await self._redis.set(key, str(now), ex=max(int(self._min_interval_sec * 2), 2))
                return

            await asyncio.sleep(min(self._min_interval_sec - elapsed, 0.25))

    async def _wait_local(self, scope: str) -> None:
        import time

        now = time.time()
        last = self._local_last_request.get(scope, 0.0)
        elapsed = now - last
        if elapsed < self._min_interval_sec:
            await asyncio.sleep(self._min_interval_sec - elapsed)
        self._local_last_request[scope] = time.time()


class RedditApiCollector:
    """Fetches posts and comments from the public Reddit JSON API."""

    def __init__(
        self,
        *,
        settings: RedditCollectorSettings | None = None,
        rate_limiter: RedditRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or RedditCollectorSettings()
        self._rate_limiter = rate_limiter or RedditRateLimiter(
            min_interval_sec=self._settings.rate_limit_interval_sec,
        )
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> RedditApiCollector:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                headers={"User-Agent": self._settings.user_agent},
                timeout=self._settings.request_timeout_sec,
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *_args) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_posts(
        self,
        config: RedditSourceConfig,
        *,
        subreddit: str,
        source_id: UUID,
    ) -> list[RedditPost]:
        path = f"/r/{subreddit}/{config.sort}.json"
        params: dict[str, Any] = {"limit": config.limit}
        if config.sort == "top":
            params["t"] = config.time_filter

        payload = await self._get_json(
            path,
            params=params,
            rate_scope=f"{source_id}:{subreddit}:posts",
        )
        posts: list[RedditPost] = []
        for child in (payload.get("data") or {}).get("children") or []:
            post = RedditPost.from_listing(child)
            if post is not None:
                posts.append(post)
        return posts

    async def fetch_comments(
        self,
        config: RedditSourceConfig,
        *,
        subreddit: str,
        post: RedditPost,
        source_id: UUID,
    ) -> list[RedditComment]:
        path = f"/r/{subreddit}/comments/{post.post_id}.json"
        params = {"limit": config.comment_limit, "depth": 1, "sort": "new"}

        payload = await self._get_json(
            path,
            params=params,
            rate_scope=f"{source_id}:{subreddit}:comments:{post.post_id}",
        )

        comments: list[RedditComment] = []
        if not isinstance(payload, list) or len(payload) < 2:
            return comments

        comment_listing = payload[1]
        for child in (comment_listing.get("data") or {}).get("children") or []:
            if child.get("kind") == "more":
                continue
            comment = RedditComment.from_listing(child, post=post)
            if comment is not None:
                comments.append(comment)
        return comments

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any],
        rate_scope: str,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("RedditApiCollector client is not initialized")

        last_error: Exception | None = None
        for attempt in range(1, self._settings.max_retries + 1):
            await self._rate_limiter.wait(rate_scope)
            try:
                response = await self._client.get(path, params=params)
                if response.status_code == 429:
                    raise httpx.HTTPStatusError(
                        "rate limited",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= self._settings.max_retries:
                    break
                backoff = self._settings.retry_backoff_sec * (2 ** (attempt - 1))
                logger.warning(
                    "Reddit request failed; retrying",
                    extra={"path": path, "attempt": attempt, "backoff_sec": backoff},
                )
                await asyncio.sleep(backoff)

        assert last_error is not None
        raise last_error
