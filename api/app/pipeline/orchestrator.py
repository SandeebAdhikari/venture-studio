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
from app.exceptions import ConflictError, NotFoundError
from app.logging import get_logger
from app.pipeline.constants import PIPELINE_STAGE_ORDER
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

    async def run_pipeline(
        self,
        *,
        trigger: PipelineTrigger = PipelineTrigger.API,
        options: PipelineRunOptions | None = None,
    ) -> PipelineRunResult:
        opts = options or PipelineRunOptions()
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
        await self._audit(run, "pipeline_started", {"stage_count": len(stages_to_run)})

        completed = 0
        failed = 0
        skipped = 0
        first_error: str | None = None
        stop = False

        try:
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

                outcome = await self._run_stage_with_retries(run, stage_run, stage, opts)
                stage_status = PipelineStageStatus(stage_run.status)
                if stage_status == PipelineStageStatus.COMPLETED:
                    completed += 1
                    await self._audit(
                        run,
                        "stage_completed",
                        {
                            "stage": stage.value,
                            "items_in": outcome.items_in,
                            "items_out": outcome.items_out,
                            "items_failed": outcome.items_failed,
                            "duration_ms": stage_run.duration_ms,
                        },
                    )
                elif stage_status == PipelineStageStatus.FAILED:
                    failed += 1
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
                metrics = await self._execute_stage(stage, opts)
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
        )
        return stage_run

    async def _execute_stage(
        self,
        stage: PipelineStage,
        opts: PipelineRunOptions,
    ) -> StageExecutionResult:
        services = self._services

        if stage == PipelineStage.COLLECT:
            result = await services.collection.collect_enabled_sources()
            return StageExecutionResult(
                items_in=result.sources_found,
                items_out=result.inserted,
                items_failed=result.sources_failed,
                records_processed=result.sources_processed + result.sources_skipped,
                metadata={"sources_skipped": result.sources_skipped, "duplicates": result.duplicates},
                failed=result.sources_failed > 0 and result.sources_processed == 0,
                error="All source collectors failed" if result.sources_failed > 0 and result.sources_processed == 0 else None,
            )

        if stage == PipelineStage.CLASSIFY:
            batch_size = opts.classify_batch_size or self._settings.classify_batch_size
            max_batches = opts.classify_max_batches or self._settings.pipeline_classify_max_batches
            total_in = 0
            total_out = 0
            total_failed = 0
            batches = 0
            while batches < max_batches:
                pending = await self._repos.signals.count_pending()
                if pending == 0:
                    break
                total_in += pending
                batch = await services.classification.classify_pending(limit=batch_size)
                total_out += batch.classified
                total_failed += batch.failed
                batches += 1
                if batch.classified + batch.skipped + batch.failed == 0:
                    break
            return StageExecutionResult(
                items_in=total_in,
                items_out=total_out,
                items_failed=total_failed,
                records_processed=batches,
                metadata={"batches": batches},
            )

        if stage == PipelineStage.GENERATE_OPPORTUNITIES:
            result = await services.generation.generate()
            return StageExecutionResult(
                items_in=result.patterns_found,
                items_out=result.created,
                items_failed=result.failed,
                records_processed=len(result.items),
                metadata={"skipped": result.skipped},
            )

        if stage == PipelineStage.SCORE_OPPORTUNITIES:
            limit = opts.score_limit or self._settings.pipeline_score_limit
            records = await services.scoring.score_all(limit=limit)
            return StageExecutionResult(
                items_in=limit,
                items_out=len(records),
                records_processed=len(records),
            )

        if stage == PipelineStage.MARKET_RESEARCH:
            result = await services.market_research.research_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.COMPETITOR_ANALYSIS:
            result = await services.competitor_intelligence.analyze_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.CUSTOMER_RESEARCH:
            result = await services.customer_research.research_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.REVENUE_VALIDATION:
            result = await services.revenue_validation.validate_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.PRODUCT_STRATEGY:
            result = await services.product_strategy.plan_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.GO_TO_MARKET:
            result = await services.go_to_market.plan_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.GROWTH_STRATEGY:
            result = await services.growth_strategy.evaluate_pending(force=opts.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.HUMAN_PROXY:
            result = await services.human_proxy.evaluate_pending(
                force=opts.force,
                founder_profile_id=opts.founder_profile_id,
            )
            return self._agent_batch_result(result)

        if stage == PipelineStage.EXECUTIVE_RANKING:
            top_n = opts.top_n or self._settings.executive_ranking_top_n
            ranking = await services.executive_ranking.generate_ranking(
                top_n=top_n,
                founder_profile_id=opts.founder_profile_id,
            )
            return StageExecutionResult(
                items_out=ranking.ranked_opportunity_count,
                records_processed=ranking.ranked_opportunity_count,
                metadata={
                    "ranking_run_id": str(ranking.ranking_run_id),
                    "top_n": ranking.top_n,
                },
            )

        if stage == PipelineStage.VENTURE_REPORT:
            top_n = opts.top_n or self._settings.executive_venture_report_top_n
            report = await services.venture_reports.generate_venture_report(
                top_n=top_n,
                founder_profile_id=opts.founder_profile_id,
                generate_ranking_if_missing=False,
                publish=True,
            )
            return StageExecutionResult(
                items_out=1,
                records_processed=report.opportunity_count,
                metadata={
                    "report_id": str(report.report_id),
                    "ranking_run_id": str(report.ranking_run_id),
                },
            )

        raise ValueError(f"Unsupported pipeline stage: {stage}")

    @staticmethod
    def _agent_batch_result(result) -> StageExecutionResult:
        return StageExecutionResult(
            items_in=getattr(result, "opportunities_found", 0),
            items_out=getattr(result, "completed", 0),
            items_failed=getattr(result, "failed", 0),
            records_processed=len(getattr(result, "items", [])),
            metadata={"skipped": getattr(result, "skipped", 0)},
        )

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
            raise ConflictError(
                f"Pipeline run '{running.id}' is already in progress"
            )

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
