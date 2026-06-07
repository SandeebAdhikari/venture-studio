"""Shared pipeline stage execution for orchestrator and background workers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from app.db.enums import PipelineStage
from app.pipeline.schemas import StageExecutionResult, build_stage_execution_result
from app.repositories import RepositoryContainer
from app.schemas.pipeline import PipelineRunOptions

if TYPE_CHECKING:
    from app.services.container import ServiceContainer


class PipelineStageExecutor:
    """Runs a single pipeline stage against the service layer."""

    def __init__(
        self,
        repos: RepositoryContainer,
        services: ServiceContainer,
        settings: Settings | None = None,
    ) -> None:
        self._repos = repos
        self._services = services
        self._settings = settings or get_settings()

    async def execute(
        self,
        stage: PipelineStage,
        opts: PipelineRunOptions | None = None,
    ) -> StageExecutionResult:
        options = opts or PipelineRunOptions()
        services = self._services

        if stage == PipelineStage.COLLECT:
            result = await services.collection.collect_enabled_sources()
            return StageExecutionResult(
                items_in=result.sources_found,
                items_out=result.inserted,
                items_failed=result.sources_failed,
                records_processed=result.sources_processed + result.sources_skipped,
                metadata={
                    "sources_skipped": result.sources_skipped,
                    "duplicates": result.duplicates,
                },
                failed=result.sources_failed > 0 and result.sources_processed == 0,
                error=(
                    "All source collectors failed"
                    if result.sources_failed > 0 and result.sources_processed == 0
                    else None
                ),
            )

        if stage == PipelineStage.CLASSIFY:
            batch_size = options.classify_batch_size or self._settings.classify_batch_size
            max_batches = (
                options.classify_max_batches or self._settings.pipeline_classify_max_batches
            )
            total_in = 0
            total_out = 0
            total_failed = 0
            total_skipped = 0
            batches = 0
            while batches < max_batches:
                pending = await self._repos.signals.count_pending()
                if pending == 0:
                    break
                total_in += pending
                batch = await services.classification.classify_pending(
                    limit=batch_size,
                    pipeline_options=options,
                )
                total_out += batch.classified
                total_failed += batch.failed
                total_skipped += batch.skipped
                batches += 1
                if batch.classified + batch.skipped + batch.failed == 0:
                    break
            return build_stage_execution_result(
                items_in=total_in,
                items_out=total_out,
                items_failed=total_failed,
                skipped=total_skipped,
                records_processed=batches,
                metadata={"batches": batches},
            )

        if stage == PipelineStage.GENERATE_OPPORTUNITIES:
            result = await services.generation.generate()
            return build_stage_execution_result(
                items_in=result.patterns_found,
                items_out=result.created,
                items_failed=result.failed,
                skipped=result.skipped,
                records_processed=len(result.items),
            )

        if stage == PipelineStage.SCORE_OPPORTUNITIES:
            limit = options.score_limit or self._settings.pipeline_score_limit
            records = await services.scoring.score_all(limit=limit)
            return StageExecutionResult(
                items_in=limit,
                items_out=len(records),
                records_processed=len(records),
            )

        if stage == PipelineStage.MARKET_RESEARCH:
            result = await services.market_research.research_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.COMPETITOR_ANALYSIS:
            result = await services.competitor_intelligence.analyze_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.CUSTOMER_RESEARCH:
            result = await services.customer_research.research_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.REVENUE_VALIDATION:
            result = await services.revenue_validation.validate_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.PRODUCT_STRATEGY:
            result = await services.product_strategy.plan_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.GO_TO_MARKET:
            result = await services.go_to_market.plan_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.GROWTH_STRATEGY:
            result = await services.growth_strategy.evaluate_pending(force=options.force)
            return self._agent_batch_result(result)

        if stage == PipelineStage.HUMAN_PROXY:
            result = await services.human_proxy.evaluate_pending(
                force=options.force,
                founder_profile_id=options.founder_profile_id,
            )
            return self._agent_batch_result(result)

        if stage == PipelineStage.EXECUTIVE_RANKING:
            top_n = options.top_n or self._settings.executive_ranking_top_n
            ranking = await services.executive_ranking.generate_ranking(
                top_n=top_n,
                founder_profile_id=options.founder_profile_id,
                discovery_validation_mode=options.discovery_validation_mode,
                pipeline_run_id=options.pipeline_run_id,
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
            from app.exceptions import ValidationError

            top_n = options.top_n or self._settings.executive_venture_report_top_n
            ranking_run_id = options.validation_ranking_run_id
            if options.discovery_validation_mode:
                if ranking_run_id is None:
                    raise ValidationError(
                        "Validation run requires executive ranking from the same pipeline run"
                    )
            report = await services.venture_reports.generate_venture_report(
                top_n=top_n,
                founder_profile_id=options.founder_profile_id,
                ranking_run_id=ranking_run_id,
                generate_ranking_if_missing=False,
                discovery_validation_mode=options.discovery_validation_mode,
                pipeline_run_id=options.pipeline_run_id,
                publish=True,
            )
            ranking_run_id = report.content.executive_ranking_run_id
            metadata: dict[str, str | int] = {
                "report_id": str(report.report_id),
                "generated_count": report.content.generated_count,
            }
            if ranking_run_id is not None:
                metadata["ranking_run_id"] = str(ranking_run_id)
            return StageExecutionResult(
                items_out=1,
                records_processed=report.content.generated_count,
                metadata=metadata,
            )

        raise ValueError(f"Unsupported pipeline stage: {stage}")

    @staticmethod
    def _agent_batch_result(result) -> StageExecutionResult:
        skipped = getattr(result, "skipped", 0)
        return build_stage_execution_result(
            items_in=getattr(result, "opportunities_found", 0),
            items_out=getattr(result, "completed", 0),
            items_failed=getattr(result, "failed", 0),
            skipped=skipped,
            records_processed=len(getattr(result, "items", [])),
        )
