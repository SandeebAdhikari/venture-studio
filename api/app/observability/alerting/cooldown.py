"""Cooldown storage for alert deduplication."""

from __future__ import annotations

import time
from typing import Protocol

from redis.asyncio import Redis

from app.config import Settings, get_settings

COOLDOWN_KEY_PREFIX = "observability:alert:cooldown:"


class CooldownStore(Protocol):
    async def is_suppressed(self, key: str, cooldown_sec: int) -> bool: ...

    async def mark_fired(self, key: str, cooldown_sec: int) -> None: ...


class InMemoryCooldownStore:
    """Process-local cooldown store for tests."""

    def __init__(self) -> None:
        self._expires: dict[str, float] = {}

    async def is_suppressed(self, key: str, cooldown_sec: int) -> bool:
        del cooldown_sec
        expires = self._expires.get(key)
        if expires is None:
            return False
        if expires <= time.monotonic():
            self._expires.pop(key, None)
            return False
        return True

    async def mark_fired(self, key: str, cooldown_sec: int) -> None:
        self._expires[key] = time.monotonic() + cooldown_sec


class RedisCooldownStore:
    def __init__(self, redis: Redis, settings: Settings | None = None) -> None:
        self._redis = redis
        self._settings = settings or get_settings()

    def _key(self, key: str) -> str:
        return f"{self._settings.alert_cooldown_key_prefix}{key}"

    async def is_suppressed(self, key: str, cooldown_sec: int) -> bool:
        return await self._redis.exists(self._key(key)) > 0

    async def mark_fired(self, key: str, cooldown_sec: int) -> None:
        await self._redis.set(self._key(key), "1", ex=cooldown_sec)
