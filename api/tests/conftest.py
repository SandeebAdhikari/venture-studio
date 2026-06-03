"""Shared pytest fixtures for API integration tests."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session_factory, init_db
from app.main import app
from app.redis.client import init_redis
from app.workers.enqueue import close_arq_pool


@pytest.fixture(autouse=True)
def _disable_scheduler(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    settings = get_settings()
    init_db(settings)
    init_redis(settings)

    factory = get_session_factory()
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_job_enqueuer():
        from app.config import get_settings
        from app.workers.enqueue import JobEnqueuer, close_arq_pool, get_arq_pool

        await close_arq_pool()
        pool = await get_arq_pool(get_settings())
        return JobEnqueuer(pool, get_settings())

    app.dependency_overrides.clear()

    from app.api.deps import get_db, get_job_enqueuer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_job_enqueuer] = override_job_enqueuer

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client

    app.dependency_overrides.clear()
    await close_arq_pool()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": get_settings().api_key}
