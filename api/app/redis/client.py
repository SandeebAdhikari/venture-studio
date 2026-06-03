"""Redis connection management."""

from redis.asyncio import ConnectionPool, Redis

from app.config import Settings, get_settings
from app.logging import get_logger

logger = get_logger(__name__)

_pool: ConnectionPool | None = None
_client: Redis | None = None


def init_redis(settings: Settings | None = None) -> None:
    """Initialize Redis connection pool (called at startup)."""
    global _pool, _client

    settings = settings or get_settings()
    _pool = ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        health_check_interval=30,
    )
    _client = Redis(connection_pool=_pool)
    logger.info("Redis connection pool initialized")


async def close_redis() -> None:
    """Close Redis connections (called at shutdown)."""
    global _pool, _client

    if _client is not None:
        await _client.aclose()
        logger.info("Redis client closed")

    if _pool is not None:
        await _pool.aclose()

    _client = None
    _pool = None


def get_redis_client() -> Redis:
    if _client is None:
        raise RuntimeError("Redis client is not initialized. Call init_redis() first.")
    return _client
