"""ARQ background job definitions for Venture Studio pipeline stages."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.enums import PipelineStage, PipelineTrigger
from app.logging import get_logger
from app.pipeline.executor import PipelineStageExecutor
from app.schemas.pipeline import PipelineRunOptions
from app.workers.context import get_worker_redis, get_worker_settings, worker_session
from app.workers.monitoring import JobMonitor
from app.workers.schemas import JobOptions

logger = get_logger(__name__)

STAGE_JOB_MAP: dict[str, PipelineStage] = {
    "collect": PipelineStage.COLLECT,
    "classify": PipelineStage.CLASSIFY,
    "generate_opportunities": PipelineStage.GENERATE_OPPORTUNITIES,
    "score": PipelineStage.SCORE_OPPORTUNITIES,
    "market_research": PipelineStage.MARKET_RESEARCH,
    "competitor_analysis": PipelineStage.COMPETITOR_ANALYSIS,
    "customer_research": PipelineStage.CUSTOMER_RESEARCH,
    "revenue_validation": PipelineStage.REVENUE_VALIDATION,
    "product_strategy": PipelineStage.PRODUCT_STRATEGY,
    "go_to_market": PipelineStage.GO_TO_MARKET,
    "growth_strategy": PipelineStage.GROWTH_STRATEGY,
    "human_proxy": PipelineStage.HUMAN_PROXY,
    "executive_ranking": PipelineStage.EXECUTIVE_RANKING,
    "venture_report": PipelineStage.VENTURE_REPORT,
}


def _parse_options(raw: dict[str, Any] | None) -> JobOptions:
    if not raw:
        return JobOptions()
    return JobOptions.model_validate(raw)


def _to_pipeline_options(job_options: JobOptions) -> PipelineRunOptions:
    return PipelineRunOptions(
        force=job_options.force,
        founder_profile_id=job_options.founder_profile_id,
        top_n=job_options.top_n,
        classify_batch_size=job_options.classify_batch_size,
        classify_max_batches=job_options.classify_max_batches,
        score_limit=job_options.score_limit,
    )


async def _acquire_job_lock(
    ctx: dict,
    job_name: str,
    idempotency_key: str | None,
) -> tuple[bool, str | None]:
    if not idempotency_key:
        return True, None

    settings = get_worker_settings(ctx)
    redis = get_worker_redis(ctx)
    lock_key = f"lock:job:{job_name}:{idempotency_key}"
    token = ctx.get("worker_id", "worker")
    acquired = await redis.set(lock_key, token, nx=True, ex=settings.arq_job_lock_ttl_sec)
    return bool(acquired), lock_key if acquired else None


async def _release_job_lock(ctx: dict, lock_key: str | None) -> None:
    if lock_key is None:
        return
    redis = get_worker_redis(ctx)
    token = ctx.get("worker_id", "worker")
    current = await redis.get(lock_key)
    if current == token:
        await redis.delete(lock_key)


async def _run_tracked_job(
    ctx: dict,
    job_name: str,
    *,
    options: dict[str, Any] | None = None,
    runner,
) -> dict[str, Any]:
    job_id = ctx["job_id"]
    attempt = ctx["job_try"]
    max_tries = ctx["max_tries"]
    redis = get_worker_redis(ctx)
    monitor = JobMonitor(redis, get_worker_settings(ctx))
    job_options = _parse_options(options)

    await monitor.record_started(
        job_id=job_id,
        job_name=job_name,
        attempt=attempt,
        max_tries=max_tries,
        worker_id=ctx.get("worker_id"),
        kwargs=options or {},
    )

    acquired, lock_key = await _acquire_job_lock(ctx, job_name, job_options.idempotency_key)
    if not acquired:
        skipped = {
            "status": "skipped",
            "reason": "duplicate_job_in_progress",
            "job_name": job_name,
        }
        await monitor.record_completed(job_id=job_id, result=skipped)
        logger.info(
            "Job skipped — lock held",
            extra={"job_id": job_id, "job_name": job_name},
        )
        return skipped

    try:
        result = await runner(job_options)
        if isinstance(result, dict) and result.get("status") == "failed":
            raise RuntimeError(str(result.get("error") or f"{job_name} failed"))
        await monitor.record_completed(job_id=job_id, result=result)
        logger.info(
            "Job completed",
            extra={"job_id": job_id, "job_name": job_name, "attempt": attempt},
        )
        return result
    except Exception as exc:
        await monitor.record_failed(
            job_id=job_id,
            error=str(exc),
            attempt=attempt,
            max_tries=max_tries,
        )
        logger.exception(
            "Job failed",
            extra={
                "job_id": job_id,
                "job_name": job_name,
                "attempt": attempt,
                "max_tries": max_tries,
            },
        )
        raise
    finally:
        await _release_job_lock(ctx, lock_key)


async def _execute_stage_job(
    ctx: dict,
    stage: PipelineStage,
    job_name: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async def runner(job_options: JobOptions) -> dict[str, Any]:
        async with worker_session() as (services, repos):
            executor = PipelineStageExecutor(repos, services, get_worker_settings(ctx))
            result = await executor.execute(stage, _to_pipeline_options(job_options))
            payload = result.model_dump(mode="json")
            payload["job_name"] = job_name
            payload["stage"] = stage.value
            if result.failed:
                payload["status"] = "failed"
            else:
                payload["status"] = "completed"
            return payload

    return await _run_tracked_job(ctx, job_name, options=options, runner=runner)


async def collect(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.COLLECT, "collect", options)


async def classify(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.CLASSIFY, "classify", options)


async def generate_opportunities(
    ctx: dict, options: dict[str, Any] | None = None
) -> dict[str, Any]:
    return await _execute_stage_job(
        ctx,
        PipelineStage.GENERATE_OPPORTUNITIES,
        "generate_opportunities",
        options,
    )


async def score(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.SCORE_OPPORTUNITIES, "score", options)


async def market_research(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.MARKET_RESEARCH, "market_research", options)


async def competitor_analysis(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(
        ctx,
        PipelineStage.COMPETITOR_ANALYSIS,
        "competitor_analysis",
        options,
    )


async def customer_research(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(
        ctx, PipelineStage.CUSTOMER_RESEARCH, "customer_research", options
    )


async def revenue_validation(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(
        ctx, PipelineStage.REVENUE_VALIDATION, "revenue_validation", options
    )


async def product_strategy(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(
        ctx, PipelineStage.PRODUCT_STRATEGY, "product_strategy", options
    )


async def go_to_market(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.GO_TO_MARKET, "go_to_market", options)


async def growth_strategy(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.GROWTH_STRATEGY, "growth_strategy", options)


async def human_proxy(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.HUMAN_PROXY, "human_proxy", options)


async def executive_ranking(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(
        ctx, PipelineStage.EXECUTIVE_RANKING, "executive_ranking", options
    )


async def venture_report(ctx: dict, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _execute_stage_job(ctx, PipelineStage.VENTURE_REPORT, "venture_report", options)


async def run_pipeline(
    ctx: dict,
    *,
    trigger: str = "api",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async def runner(_job_options: JobOptions) -> dict[str, Any]:
        async with worker_session() as (services, _repos):
            pipeline_options = PipelineRunOptions.model_validate(options or {})
            result = await services.pipeline.run_pipeline(
                trigger=PipelineTrigger(trigger),
                options=pipeline_options,
            )
            return {
                "status": "completed",
                "job_name": "run_pipeline",
                **result.model_dump(mode="json"),
            }

    return await _run_tracked_job(ctx, "run_pipeline", options=options, runner=runner)


def job_options_from_uuid(founder_profile_id: UUID | None) -> dict[str, Any]:
    return JobOptions(founder_profile_id=founder_profile_id).model_dump(mode="json")
