"""Dashboard-facing observability metrics aggregation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.db.enums import PipelineRunStatus
from app.db.models.pipeline_run import PipelineRun
from app.observability.metrics import record_metrics
from app.observability.worker_heartbeat import list_active_workers
from app.repositories import RepositoryContainer
from app.repositories.dashboard import DashboardMetricsRepository
from app.scheduler.scheduler import get_scheduler
from app.schemas.observability import DashboardObservabilityMetricsResponse

if TYPE_CHECKING:
    from redis.asyncio import Redis


class ObservabilityMetricsService:
    """Aggregates runtime and database metrics for dashboard visibility."""

    def __init__(
        self,
        repos: RepositoryContainer,
        redis: Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repos = repos
        self._redis = redis
        self._settings = settings or get_settings()
        self._metrics = DashboardMetricsRepository(repos.session)

    async def get_dashboard_metrics(self) -> DashboardObservabilityMetricsResponse:
        pipeline_counts = await self._pipeline_counts()
        classification = await self._metrics.classification_metrics()
        approval_counts = await self._repos.approval_requests.count_by_status()
        record_metrics().sync_approval_gauges(approval_counts)

        active_workers: list[str] = []
        if self._redis is not None:
            active_workers = await list_active_workers(self._redis, settings=self._settings)

        scheduler_running = False
        if self._settings.scheduler_enabled:
            try:
                scheduler_running = get_scheduler().is_running
            except Exception:
                scheduler_running = False

        running = await self._repos.pipelines.get_running()
        pending_approvals = approval_counts.get("pending", 0) + approval_counts.get(
            "research_requested", 0
        )

        return DashboardObservabilityMetricsResponse(
            generated_at=datetime.now(UTC),
            pipeline={
                "running": running is not None,
                "running_run_id": str(running.id) if running else None,
                "runs_total": sum(pipeline_counts.values()),
                "runs_by_status": pipeline_counts,
            },
            workers={
                "active_count": len(active_workers),
                "active_worker_ids": active_workers,
                "readiness_required": self._settings.worker_readiness_required,
            },
            scheduler={
                "enabled": self._settings.scheduler_enabled,
                "running": scheduler_running,
            },
            llm={
                "requests_total": classification["calls_total"],
                "cost_usd_total": classification["cost_usd_total"],
            },
            approvals={
                "pending_total": pending_approvals,
                "by_status": approval_counts,
            },
            observability={
                "metrics_enabled": self._settings.observability_metrics_enabled,
                "tracing_enabled": self._settings.observability_tracing_enabled,
                "tracing_provider": self._settings.observability_tracing_provider,
                "error_tracking_provider": self._settings.observability_error_tracking_provider,
                "prometheus_endpoint": "/metrics",
            },
        )

    async def _pipeline_counts(self) -> dict[str, int]:
        result = await self._repos.session.execute(
            select(PipelineRun.status, func.count())
            .select_from(PipelineRun)
            .group_by(PipelineRun.status)
        )
        counts = {status.value: 0 for status in PipelineRunStatus}
        for status, count in result.all():
            counts[str(status)] = int(count)
        return counts
