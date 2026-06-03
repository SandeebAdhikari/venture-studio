"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_async_session
from app.redis.client import get_redis_client
from app.services.container import ServiceContainer, get_services
from app.workers.enqueue import JobEnqueuer, get_arq_pool


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a request-scoped database session."""
    async for session in get_async_session():
        yield session


async def get_redis() -> Redis:
    """Provide the shared Redis client."""
    return get_redis_client()


def get_app_settings() -> Settings:
    """Provide application settings."""
    return get_settings()


async def get_service_container(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ServiceContainer:
    """Provide the service layer for the current request."""
    return get_services(session)


async def get_job_enqueuer() -> JobEnqueuer:
    """Provide ARQ job enqueuer backed by Redis."""
    pool = await get_arq_pool()
    return JobEnqueuer(pool)


async def verify_api_key(
    settings: Annotated[Settings, Depends(get_app_settings)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Validate the shared API key for protected routes."""
    if x_api_key is None or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# Type aliases for cleaner route signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
Services = Annotated[ServiceContainer, Depends(get_service_container)]
JobEnqueuerDep = Annotated[JobEnqueuer, Depends(get_job_enqueuer)]
Authenticated = Annotated[None, Depends(verify_api_key)]
