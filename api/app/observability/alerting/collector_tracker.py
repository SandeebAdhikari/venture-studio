"""Redis-backed consecutive collector failure tracking."""

from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis

from app.config import Settings, get_settings


class CollectorFailureTracker:
    def __init__(self, redis: Redis, settings: Settings | None = None) -> None:
        self._redis = redis
        self._settings = settings or get_settings()

    def _key(self, source_id: UUID) -> str:
        return f"{self._settings.alert_collector_failure_key_prefix}{source_id}"

    async def record_failure(self, source_id: UUID) -> int:
        key = self._key(source_id)
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._settings.alert_collector_failure_window_sec)
        return int(count)

    async def record_success(self, source_id: UUID) -> None:
        await self._redis.delete(self._key(source_id))
