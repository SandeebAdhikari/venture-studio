"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings) -> AsyncEngine:
    """Build an async SQLAlchemy engine with connection pooling."""
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
    )


def init_db(settings: Settings | None = None) -> None:
    """Initialize global engine and session factory (called at startup)."""
    global _engine, _async_session_factory

    settings = settings or get_settings()
    _engine = create_engine(settings)
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    logger.info("Database engine initialized", extra={"pool_size": settings.db_pool_size})


async def close_db() -> None:
    """Dispose engine connections (called at shutdown)."""
    global _engine, _async_session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")

    _engine = None
    _async_session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _async_session_factory is None:
        raise RuntimeError("Session factory is not initialized. Call init_db() first.")
    return _async_session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
