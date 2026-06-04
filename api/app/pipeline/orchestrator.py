"""Production-grade Venture Studio pipeline orchestrator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.config import Settings, get_settings
from app.db.enums import (
    PipelineRunStatus,
    PipelineStage,
    PipelineStageStatus,
    PipelineTrigger,
)
from app.discovery.validation import (
    DiscoveryValidationPreflight,
    resolve_pipeline_options,
)
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.logging import get_logger
from app.observability.metrics import record_metrics
from app.observability.tracing import trace_span
from app.pipeline.constants import PIPELINE_STAGE_ORDER
from app.pipeline.executor import PipelineStageExecutor
from app.pipeline.schemas import StageExecutionResult
from app.repositories import RepositoryContainer
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.pipeline import (
    PipelineRunCreate,
    PipelineRunDetail,
    PipelineRunOptions,
    PipelineRunRead,
    PipelineRunResult,
    PipelineStageRunCreate,
)

if TYPE_CHECKING:
    from app.services.container import ServiceContainer

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Executes the full Venture Studio pipeline with stage tracking and retries."""

    def __init__(
        self,
        repos: RepositoryContainer,
        services: ServiceContainer,
        settings: Settings | None = None,
    ) -> None:
        self._repos = repos
        self._services = services
        self._settings = settings or get_settings()
        self._executor = PipelineStageExecutor(repos, services, self._settings)

    async def run_pipeline(
        self,
        *,
        trigger: PipelineTrigger = PipelineTrigger.API,
        options: PipelineRunOptions | None = None,
    ) -> PipelineRunResult:
        opts = resolve_pipeline_options(options, self._settings)
        if opts.discovery_validation_mode:
            preflight = await DiscoveryValidationPreflight(self._repos).check()
            if not preflight.passed:
                raise ValidationError(
                    f"Discovery validation preflight failed: {preflight.detail}"
                )

        max_retries = (
            opts.max_retries
            if opts.max_retries is not None
            else self._settings.pipeline_max_retries
        )

        lock_token = await self._acquire_lock()
        run = await self._repos.pipelines.create_run(
            PipelineRunCreate(
                trigger=trigger,
                founder_profile_id=opts.founder_profile_id,
                config_snapshot=opts.model_dump(mode="json"),
            )
        )

        record_metrics().set_pipeline_running(True)

        stages_to_run = self._resolve_stages(opts)
        stage_plans = [
            PipelineStageRunCreate(
                stage=stage,
                sequence=index,
                max_attempts=max_retries + 1,
            )
            for index, stage in enumerate(stages_to_run, start=1)
        ]
        await self._repos.pipelines.create_stage_runs(run.id, stage_plans)
        await self._repos.pipelines.mark_run_started(run)
        opts = opts.model_copy(update={"pipeline_run_id": run.id})
        await self._audit(run, "pipeline_started", {"stage_count": len(stages_to_run)})

        completed = 0
        failed = 0
        skipped = 0
        first_error: str | None = None
        stop = False

        try:
            with trace_span(
                "pipeline.run",
                attributes={
                    "pipeline_run_id": str(run.id),
                    "trigger": trigger.value,
                    "stage_count": len(stages_to_run),
                },
            ):
                for stage in stages_to_run:
                    if stop:
                        stage_run = await self._repos.pipelines.get_stage_run(run.id, stage.value)
                        if stage_run is not None:
                            await self._repos.pipelines.mark_stage_skipped(
                                stage_run,
                                reason="prior_stage_failure",
                            )
                            skipped += 1
                            await self._audit(run, "stage_skipped", {"stage": stage.value})
                        continue

                    if stage in opts.skip_stages:
                        stage_run = await self._repos.pipelines.get_stage_run(run.id, stage.value)
                        if stage_run is not None:
                            await self._repos.pipelines.mark_stage_started(stage_run)
                            await self._repos.pipelines.mark_stage_skipped(
                                stage_run,
                                reason="explicitly_skipped",
                            )
                            skipped += 1
                            await self._audit(run, "stage_skipped", {"stage": stage.value})
                        continue

                    stage_run = await self._repos.pipelines.get_stage_run(run.id, stage.value)
                    if stage_run is None:
                        continue

                    await self._run_stage_with_retries(run, stage_run, stage, opts)
                    stage_status = PipelineStageStatus(stage_run.status)
                    if stage_status == PipelineStageStatus.COMPLETED:
                        if stage == PipelineStage.EXECUTIVE_RANKING:
                            ranking_run_id = (stage_run.stage_metadata or {}).get(
                                "ranking_run_id"
                            )
                            if ranking_run_id:
                                opts = opts.model_copy(
                                    update={
                                        "validation_ranking_run_id": UUID(
                                            str(ranking_run_id)
                                        )
                                    }
                                )
                        completed += 1
                        record_metrics().record_stage_duration(
                            stage=stage.value,
                            status=stage_status.value,
                            duration_ms=stage_run.duration_ms,
                        )
                        await self._audit(
                            run,
                            "stage_completed",
                            {
                                "stage": stage.value,
                                "items_in": stage_run.items_in,
                                "items_out": stage_run.items_out,
                                "items_failed": stage_run.items_failed,
                                "duration_ms": stage_run.duration_ms,
                            },
                        )
                    elif stage_status == PipelineStageStatus.FAILED:
                        failed += 1
                        record_metrics().record_stage_duration(
                            stage=stage.value,
                            status=stage_status.value,
                            duration_ms=stage_run.duration_ms,
                        )
                        first_error = first_error or stage_run.error_detail
                        await self._audit(
                            run,
                            "stage_failed",
                            {
                                "stage": stage.value,
                                "error": stage_run.error_detail,
                            },
                        )
                        if opts.stop_on_failure:
                            stop = True

            final_status = self._resolve_final_status(
                completed=completed,
                failed=failed,
                skipped=skipped,
                total=len(stages_to_run),
                stopped_early=stop,
            )
            await self._repos.pipelines.update_run_counters(
                run,
                stages_completed=completed,
                stages_failed=failed,
                stages_skipped=skipped,
            )
            await self._repos.pipelines.mark_run_finished(
                run,
                status=final_status,
                error_summary=first_error,
            )
            await self._audit(run, "pipeline_finished", {"status": final_status.value})

            record_metrics().record_pipeline_run(
                status=final_status.value,
                trigger=trigger.value,
            )

            if final_status.value in {"failed", "partial"}:
                from app.observability.alerting.checks import alert_pipeline_failure

                await alert_pipeline_failure(
                    pipeline_run_id=run.id,
                    status=final_status.value,
                    trigger=trigger.value,
                    error_summary=first_error,
                )

            refreshed = await self._repos.pipelines.get_by_id_with_stages(run.id)
            assert refreshed is not None

            logger.info(
                "Pipeline run finished",
                extra={
                    "pipeline_run_id": str(run.id),
                    "status": final_status.value,
                    "stages_completed": completed,
                    "stages_failed": failed,
                },
            )

            return PipelineRunResult(
                pipeline_run_id=refreshed.id,
                status=final_status,
                stages_completed=completed,
                stages_failed=failed,
                stages_skipped=skipped,
                duration_ms=refreshed.duration_ms,
            )
        finally:
            record_metrics().set_pipeline_running(False)
            await self._release_lock(lock_token)

    async def get_run(self, run_id: UUID) -> PipelineRunDetail:
        run = await self._repos.pipelines.get_by_id_with_stages(run_id)
        if run is None:
            raise NotFoundError("pipeline_run", run_id)
        return PipelineRunDetail.from_entity(run)

    async def list_runs(
        self,
        pagination: PaginationParams,
    ) -> PaginatedResponse[PipelineRunRead]:
        items = await self._repos.pipelines.list_runs(
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.pipelines.count_runs()
        return PaginatedResponse[PipelineRunRead](
            items=[PipelineRunRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def _run_stage_with_retries(
        self,
        run,
        stage_run,
        stage: PipelineStage,
        opts: PipelineRunOptions,
    ) -> Any:
        max_attempts = stage_run.max_attempts
        last_error: str | None = None
        metrics = StageExecutionResult()

        with trace_span("pipeline.stage", attributes={"stage": stage.value}):
            for attempt in range(1, max_attempts + 1):
                if attempt > 1:
                    await self._repos.pipelines.mark_stage_retrying(stage_run)
                    await self._audit(
                        run,
                        "stage_retry",
                        {"stage": stage.value, "attempt": attempt},
                    )
                    await asyncio.sleep(
                        self._settings.pipeline_retry_backoff_sec * (2 ** (attempt - 2))
                    )
                else:
                    await self._repos.pipelines.mark_stage_started(stage_run)

                try:
                    metrics = await self._executor.execute(stage, opts)
                    if metrics.failed:
                        last_error = metrics.error or "Stage reported failure"
                        if attempt < max_attempts:
                            continue
                        await self._repos.pipelines.mark_stage_failed(
                            stage_run,
                            error_detail=last_error,
                            items_in=metrics.items_in,
                            items_out=metrics.items_out,
                            items_failed=metrics.items_failed,
                            records_processed=metrics.records_processed,
                            stage_metadata=metrics.metadata,
                        )
                        return stage_run

                    await self._repos.pipelines.mark_stage_completed(
                        stage_run,
                        items_in=metrics.items_in,
                        items_out=metrics.items_out,
                        items_failed=metrics.items_failed,
                        records_processed=metrics.records_processed,
                        stage_metadata=metrics.metadata,
                    )
                    return stage_run
                except Exception as exc:
                    last_error = str(exc)
                    logger.exception(
                        "Pipeline stage error",
                        extra={"stage": stage.value, "attempt": attempt},
                    )
                    if attempt < max_attempts:
                        continue

            await self._repos.pipelines.mark_stage_failed(
                stage_run,
                error_detail=last_error or "Unknown stage failure",
                items_in=metrics.items_in,
                items_out=metrics.items_out,
                items_failed=metrics.items_failed,
                records_processed=metrics.records_processed,
                stage_metadata=metrics.metadata,
            )
        return stage_run

    @staticmethod
    def _resolve_stages(opts: PipelineRunOptions) -> list[PipelineStage]:
        if opts.stages_only:
            ordered = [stage for stage in PIPELINE_STAGE_ORDER if stage in opts.stages_only]
            return ordered
        return list(PIPELINE_STAGE_ORDER)

    @staticmethod
    def _resolve_final_status(
        *,
        completed: int,
        failed: int,
        skipped: int,
        total: int,
        stopped_early: bool,
    ) -> PipelineRunStatus:
        if failed > 0 and completed == 0:
            return PipelineRunStatus.FAILED
        if failed > 0 or stopped_early:
            return PipelineRunStatus.PARTIAL
        if skipped == total:
            return PipelineRunStatus.COMPLETED
        if completed + skipped == total:
            return PipelineRunStatus.COMPLETED
        return PipelineRunStatus.PARTIAL

    async def _acquire_lock(self) -> str | None:
        running = await self._repos.pipelines.get_running()
        if running is not None:
            raise ConflictError(f"Pipeline run '{running.id}' is already in progress")

        token = datetime.now(UTC).isoformat()
        try:
            from app.redis.client import get_redis_client

            redis = get_redis_client()
            acquired = await redis.set(
                self._settings.pipeline_lock_key,
                token,
                nx=True,
                ex=self._settings.pipeline_lock_ttl_sec,
            )
            if not acquired:
                raise ConflictError("Pipeline lock is held by another worker")
        except RuntimeError:
            return None
        return token

    async def _release_lock(self, token: str | None) -> None:
        if token is None:
            return
        try:
            from app.redis.client import get_redis_client

            redis = get_redis_client()
            current = await redis.get(self._settings.pipeline_lock_key)
            if current == token:
                await redis.delete(self._settings.pipeline_lock_key)
        except RuntimeError:
            pass

    async def _audit(self, run, event: str, payload: dict[str, Any]) -> None:
        await self._repos.pipelines.append_audit_event(
            run,
            {"event": event, **payload},
        )
