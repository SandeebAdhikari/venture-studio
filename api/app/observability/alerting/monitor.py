"""Periodic alert checks for worker, scheduler, queue, and pipeline stall."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from app.logging import get_logger
from app.observability.alerting.checks import (
    alert_pipeline_stall,
    alert_queue_backlog_growth,
    alert_scheduler_offline,
    alert_worker_offline,
)
from app.observability.alerting.engine import get_alert_engine
from app.observability.worker_heartbeat import list_active_workers
from app.scheduler.scheduler import get_scheduler

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = get_logger(__name__)

_monitor_task: asyncio.Task[None] | None = None
_last_queue_depth: int | None = None


async def get_arq_queue_depth(redis: Redis, settings: Settings) -> int:
    depth = await redis.llen(settings.arq_queue_name)
    return int(depth or 0)


async def run_alert_monitor_cycle(
    *,
    redis: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings | None = None,
) -> None:
    """Run one pass of background alert checks."""
    global _last_queue_depth

    resolved = settings or get_settings()
    engine = get_alert_engine()
    if not engine.enabled:
        return

    if resolved.alert_worker_monitor_enabled:
        workers = await list_active_workers(redis, settings=resolved)
        if not workers:
            await alert_worker_offline(engine=engine)

    if resolved.scheduler_enabled:
        try:
            scheduler = get_scheduler()
            if not scheduler.is_running:
                await alert_scheduler_offline(engine=engine)
        except Exception as exc:
            logger.warning("Scheduler alert check failed", exc_info=exc)

    depth = await get_arq_queue_depth(redis, resolved)
    if (
        _last_queue_depth is not None
        and depth >= resolved.alert_queue_backlog_threshold
        and depth - _last_queue_depth >= resolved.alert_queue_growth_delta
    ):
        await alert_queue_backlog_growth(
            queue_depth=depth,
            previous_depth=_last_queue_depth,
            delta=depth - _last_queue_depth,
            engine=engine,
        )
    _last_queue_depth = depth

    if resolved.alert_pipeline_stall_sec > 0:
        from app.repositories import get_repositories

        async with session_factory() as session:
            repos = get_repositories(session)
            running = await repos.pipelines.get_running()
            if running is not None and running.started_at is not None:
                elapsed = (datetime.now(UTC) - running.started_at).total_seconds()
                if elapsed >= resolved.alert_pipeline_stall_sec:
                    await alert_pipeline_stall(
                        pipeline_run_id=running.id,
                        stall_sec=int(elapsed),
                        started_at=running.started_at.isoformat(),
                        engine=engine,
                    )


async def _monitor_loop(
    redis: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    interval = max(settings.alert_monitor_interval_sec, 15)
    while True:
        try:
            await run_alert_monitor_cycle(
                redis=redis,
                session_factory=session_factory,
                settings=settings,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Alert monitor cycle failed", exc_info=exc)
        await asyncio.sleep(interval)


def start_alert_monitor(
    redis: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings | None = None,
) -> None:
    global _monitor_task
    resolved = settings or get_settings()
    if not resolved.alerting_enabled or not resolved.alert_monitor_enabled:
        return
    if _monitor_task is not None and not _monitor_task.done():
        return
    _monitor_task = asyncio.create_task(
        _monitor_loop(redis, session_factory, resolved),
        name="alert-monitor",
    )
    logger.info(
        "Alert monitor started",
        extra={"interval_sec": resolved.alert_monitor_interval_sec},
    )


async def stop_alert_monitor() -> None:
    global _monitor_task, _last_queue_depth
    task = _monitor_task
    _monitor_task = None
    _last_queue_depth = None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Alert monitor stopped")
