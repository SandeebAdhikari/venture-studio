"""Helpers to construct and fire domain-specific alerts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.observability.alerting.engine import get_alert_engine
from app.observability.alerting.models import Alert, AlertSeverity, AlertType

if TYPE_CHECKING:
    from app.observability.alerting.engine import AlertEngine


async def alert_worker_offline(*, engine: AlertEngine | None = None) -> bool:
    engine = engine or get_alert_engine()
    return await engine.fire(
        Alert(
            alert_type=AlertType.WORKER_OFFLINE,
            severity=AlertSeverity.CRITICAL,
            title="Worker offline",
            message="No active ARQ worker heartbeats detected",
            dedup_key="global",
            context={"component": "worker"},
        )
    )


async def alert_scheduler_offline(*, engine: AlertEngine | None = None) -> bool:
    engine = engine or get_alert_engine()
    return await engine.fire(
        Alert(
            alert_type=AlertType.SCHEDULER_OFFLINE,
            severity=AlertSeverity.CRITICAL,
            title="Scheduler offline",
            message="APScheduler is enabled but not running",
            dedup_key="global",
            context={"component": "scheduler"},
        )
    )


async def alert_pipeline_failure(
    *,
    pipeline_run_id: UUID,
    status: str,
    trigger: str,
    error_summary: str | None = None,
    engine: AlertEngine | None = None,
) -> bool:
    engine = engine or get_alert_engine()
    severity = AlertSeverity.CRITICAL if status == "failed" else AlertSeverity.WARNING
    return await engine.fire(
        Alert(
            alert_type=AlertType.PIPELINE_FAILURE,
            severity=severity,
            title=f"Pipeline {status}",
            message=error_summary or f"Pipeline run ended with status '{status}'",
            dedup_key=str(pipeline_run_id),
            context={
                "pipeline_run_id": str(pipeline_run_id),
                "status": status,
                "trigger": trigger,
            },
        )
    )


async def alert_pipeline_stall(
    *,
    pipeline_run_id: UUID,
    stall_sec: int,
    started_at: str,
    engine: AlertEngine | None = None,
) -> bool:
    engine = engine or get_alert_engine()
    return await engine.fire(
        Alert(
            alert_type=AlertType.PIPELINE_STALL,
            severity=AlertSeverity.WARNING,
            title="Pipeline stall detected",
            message=(
                f"Pipeline run {pipeline_run_id} has been running for "
                f"at least {stall_sec}s (started {started_at})"
            ),
            dedup_key=str(pipeline_run_id),
            context={
                "pipeline_run_id": str(pipeline_run_id),
                "stall_sec": stall_sec,
                "started_at": started_at,
            },
        )
    )


async def alert_queue_backlog_growth(
    *,
    queue_depth: int,
    previous_depth: int,
    delta: int,
    engine: AlertEngine | None = None,
) -> bool:
    engine = engine or get_alert_engine()
    return await engine.fire(
        Alert(
            alert_type=AlertType.QUEUE_BACKLOG_GROWTH,
            severity=AlertSeverity.WARNING,
            title="ARQ queue backlog growing",
            message=(
                f"Queue depth {queue_depth} increased by {delta} "
                f"(previous {previous_depth})"
            ),
            dedup_key="global",
            context={
                "queue_depth": queue_depth,
                "previous_depth": previous_depth,
                "delta": delta,
            },
        )
    )


async def alert_llm_budget_exhausted(
    *,
    spent_usd: float,
    budget_usd: float,
    threshold_pct: int | None = None,
    graph_name: str | None = None,
    engine: AlertEngine | None = None,
) -> bool:
    engine = engine or get_alert_engine()
    if threshold_pct is not None:
        dedup_key = f"threshold:{threshold_pct}"
        title = f"LLM budget at {threshold_pct}%"
        message = (
            f"Daily LLM spend ${spent_usd:.4f} reached {threshold_pct}% "
            f"of budget ${budget_usd:.2f}"
        )
        severity = AlertSeverity.WARNING if threshold_pct < 100 else AlertSeverity.CRITICAL
    else:
        dedup_key = "exhausted"
        title = "LLM budget exhausted"
        message = (
            f"Daily LLM budget exceeded: spent ${spent_usd:.4f} "
            f"of ${budget_usd:.2f}"
        )
        severity = AlertSeverity.CRITICAL

    context: dict[str, Any] = {
        "spent_usd": spent_usd,
        "budget_usd": budget_usd,
    }
    if threshold_pct is not None:
        context["threshold_pct"] = threshold_pct
    if graph_name:
        context["graph_name"] = graph_name

    return await engine.fire(
        Alert(
            alert_type=AlertType.LLM_BUDGET_EXHAUSTED,
            severity=severity,
            title=title,
            message=message,
            dedup_key=dedup_key,
            context=context,
        )
    )


async def alert_collector_repeated_failure(
    *,
    source_id: UUID,
    source_name: str,
    source_type: str,
    failure_count: int,
    last_error: str,
    engine: AlertEngine | None = None,
) -> bool:
    engine = engine or get_alert_engine()
    return await engine.fire(
        Alert(
            alert_type=AlertType.COLLECTOR_REPEATED_FAILURE,
            severity=AlertSeverity.WARNING,
            title="Repeated collector failures",
            message=(
                f"Source '{source_name}' ({source_type}) failed {failure_count} "
                f"times in a row: {last_error}"
            ),
            dedup_key=str(source_id),
            context={
                "source_id": str(source_id),
                "source_name": source_name,
                "source_type": source_type,
                "failure_count": failure_count,
                "last_error": last_error,
            },
        )
    )
