"""Worker heartbeat tracking in Redis for readiness probes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.config import Settings, get_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis


def worker_heartbeat_key(worker_id: str, settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return f"{resolved.worker_heartbeat_key_prefix}{worker_id}"


async def refresh_worker_heartbeat(
    redis: Redis,
    worker_id: str,
    *,
    settings: Settings | None = None,
) -> None:
    resolved = settings or get_settings()
    key = worker_heartbeat_key(worker_id, resolved)
    payload = datetime.now(UTC).isoformat()
    await redis.set(key, payload, ex=resolved.worker_heartbeat_ttl_sec)


async def clear_worker_heartbeat(
    redis: Redis,
    worker_id: str,
    *,
    settings: Settings | None = None,
) -> None:
    await redis.delete(worker_heartbeat_key(worker_id, settings))


async def list_active_workers(
    redis: Redis,
    *,
    settings: Settings | None = None,
) -> list[str]:
    resolved = settings or get_settings()
    prefix = resolved.worker_heartbeat_key_prefix
    active: list[str] = []
    async for key in redis.scan_iter(match=f"{prefix}*"):
        key_str = key.decode() if isinstance(key, bytes) else str(key)
        if key_str.startswith(prefix):
            active.append(key_str.removeprefix(prefix))
    return active
