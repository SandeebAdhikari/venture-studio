"""Low-level Hacker News Algolia search API client."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import httpx

from app.collectors.hn_algolia.models import (
    HnAlgoliaCollectorSettings,
    HnAlgoliaSearchResult,
    HnAlgoliaSourceConfig,
    HnAlgoliaStory,
)
from app.logging import get_logger

logger = get_logger(__name__)


class HnAlgoliaRateLimiter:
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

        key = f"ratelimit:hn_algolia:{scope}"
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


class HnAlgoliaApiCollector:
    """Fetches Hacker News stories via the public Algolia search API."""

    def __init__(
        self,
        *,
        settings: HnAlgoliaCollectorSettings | None = None,
        rate_limiter: HnAlgoliaRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or HnAlgoliaCollectorSettings()
        self._rate_limiter = rate_limiter or HnAlgoliaRateLimiter(
            min_interval_sec=self._settings.rate_limit_interval_sec,
        )
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> HnAlgoliaApiCollector:
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

    async def fetch_stories(
        self,
        config: HnAlgoliaSourceConfig,
        *,
        source_id: UUID,
    ) -> HnAlgoliaSearchResult:
        stories: list[HnAlgoliaStory] = []
        nb_pages = config.max_pages
        pages_fetched = 0

        for page in range(config.max_pages):
            payload = await self._search_page(
                config,
                page=page,
                source_id=source_id,
            )
            pages_fetched += 1
            nb_pages = min(nb_pages, int(payload.get("nbPages") or 0) or config.max_pages)

            hits = payload.get("hits") or []
            if not hits:
                break

            for hit in hits:
                story = HnAlgoliaStory.from_hit(hit)
                if story is not None:
                    stories.append(story)

            current_page = int(payload.get("page") or page)
            if current_page + 1 >= nb_pages:
                break

        return HnAlgoliaSearchResult(stories=stories, pages_fetched=pages_fetched)

    async def _search_page(
        self,
        config: HnAlgoliaSourceConfig,
        *,
        page: int,
        source_id: UUID,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": config.query,
            "tags": config.tags,
            "page": page,
            "hitsPerPage": config.hits_per_page,
        }
        payload = await self._get_json(
            "/search",
            params=params,
            rate_scope=f"{source_id}:search:{page}",
        )
        if not isinstance(payload, dict):
            raise ValueError("HN Algolia search returned unexpected payload")
        return payload

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any],
        rate_scope: str,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("HnAlgoliaApiCollector client is not initialized")

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
                    "HN Algolia request failed; retrying",
                    extra={"path": path, "attempt": attempt, "backoff_sec": backoff},
                )
                await asyncio.sleep(backoff)

        assert last_error is not None
        raise last_error
