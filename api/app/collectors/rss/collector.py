"""Low-level RSS feed fetcher."""

from __future__ import annotations

import asyncio
from uuid import UUID

import feedparser
import httpx

from app.collectors.rss.models import RssCollectorSettings, RssFeedEntry
from app.logging import get_logger

logger = get_logger(__name__)


class RssRateLimiter:
    """Rate limiter for RSS polling with Redis or in-process fallback."""

    def __init__(self, *, redis=None, min_interval_sec: float = 1.0) -> None:
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

        key = f"ratelimit:rss:{scope}"
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


class RssFeedCollector:
    """Downloads and parses RSS/Atom feeds."""

    def __init__(
        self,
        *,
        settings: RssCollectorSettings | None = None,
        rate_limiter: RssRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or RssCollectorSettings()
        self._rate_limiter = rate_limiter or RssRateLimiter(
            min_interval_sec=self._settings.rate_limit_interval_sec,
        )
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> RssFeedCollector:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self._settings.user_agent},
                timeout=self._settings.request_timeout_sec,
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *_args) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_entries(
        self,
        feed_url: str,
        *,
        entry_limit: int,
        source_id: UUID,
    ) -> list[RssFeedEntry]:
        if self._client is None:
            raise RuntimeError("RssFeedCollector client is not initialized")

        last_error: Exception | None = None
        for attempt in range(1, self._settings.max_retries + 1):
            await self._rate_limiter.wait(f"{source_id}:fetch")
            try:
                response = await self._client.get(feed_url)
                if response.status_code == 429:
                    raise httpx.HTTPStatusError(
                        "rate limited",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
                if getattr(parsed, "bozo", False) and not parsed.entries:
                    raise ValueError(getattr(parsed, "bozo_exception", "Invalid RSS feed"))

                feed_title = getattr(parsed.feed, "title", None) if hasattr(parsed, "feed") else None
                entries: list[RssFeedEntry] = []
                for entry in parsed.entries[:entry_limit]:
                    mapped = RssFeedEntry.from_feedparser_entry(entry, feed_title=feed_title)
                    if mapped is not None:
                        entries.append(mapped)
                return entries
            except (httpx.HTTPStatusError, httpx.TransportError, ValueError) as exc:
                last_error = exc
                if attempt >= self._settings.max_retries:
                    break
                backoff = self._settings.retry_backoff_sec * (2 ** (attempt - 1))
                logger.warning(
                    "RSS fetch failed; retrying",
                    extra={"feed_url": feed_url, "attempt": attempt, "backoff_sec": backoff},
                )
                await asyncio.sleep(backoff)

        assert last_error is not None
        raise last_error
