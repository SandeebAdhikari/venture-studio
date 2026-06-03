"""Orchestrates growth strategy evaluation for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.growth_strategy.graph import GRAPH_NAME, GrowthStrategyAgent
from app.agents.growth_strategy.llm_client import (
    GrowthStrategyLLMClient,
    OpenAIGrowthStrategyClient,
)
from app.agents.growth_strategy.schemas import (
    ComplaintEvidenceItem,
    GrowthStrategyBatchResult,
    GrowthStrategyResult,
    OpportunityGrowthContext,
)
from app.config import Settings, get_settings
from app.db.enums import GrowthEvaluationStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import GrowthEvaluationListFilter
from app.schemas.growth_evaluation import (
    GrowthEvaluationCreate,
    GrowthEvaluationDetail,
    GrowthEvaluationEvidenceCreate,
    GrowthEvaluationRead,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class GrowthStrategyService:
    """Evaluates long-term growth potential for opportunities."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: GrowthStrategyLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: GrowthStrategyAgent | None = None

    def _get_agent(self) -> GrowthStrategyAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIGrowthStrategyClient(self._settings)
            self._agent = GrowthStrategyAgent(
                client,
                self._settings,
                budget_service=self._budget,
            )
        return self._agent

    async def evaluate_pending(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> GrowthStrategyBatchResult:
        batch_size = limit or self._settings.growth_strategy_batch_size
        if force:
            opportunity_ids = await self._repos.growth_evaluations.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = (
                await self._repos.growth_evaluations.list_opportunity_ids_without_evaluation(
                    limit=batch_size,
                )
            )

        batch_result = GrowthStrategyBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.evaluate_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Growth strategy batch complete",
            extra={
                "opportunities_found": batch_result.opportunities_found,
                "completed": batch_result.completed,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def evaluate_opportunity(
        self,
        opportunity_id: UUID,
        *,
        force: bool = False,
    ) -> GrowthStrategyResult:
        if not force:
            existing = await self._repos.growth_evaluations.get_current_for_opportunity(
                opportunity_id,
            )
            if existing is not None and existing.status == GrowthEvaluationStatus.COMPLETED.value:
                return GrowthStrategyResult(
                    opportunity_id=opportunity_id,
                    growth_evaluation_id=existing.id,
                    status="skipped",
                    skip_reason="already_evaluated",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            return agent_result

        model = self._last_model(agent_result) or self._settings.growth_strategy_model
        draft = agent_result.draft
        evaluation = await self._repos.growth_evaluations.create(
            GrowthEvaluationCreate(
                opportunity_id=opportunity_id,
                status=GrowthEvaluationStatus.COMPLETED,
                growth_score=draft.growth_score,
                scalability_score=draft.scalability_score,
                risk_score=draft.risk_score,
                seo_potential=draft.seo_potential.model_dump(),
                referral_potential=draft.referral_potential.model_dump(),
                partnership_opportunities=[
                    item.model_dump() for item in draft.partnership_opportunities
                ],
                paid_acquisition_potential=draft.paid_acquisition_potential.model_dump(),
                market_expansion_opportunities=[
                    item.model_dump() for item in draft.market_expansion_opportunities
                ],
                growth_roadmap=draft.growth_roadmap,
                executive_summary=draft.executive_summary,
                evaluation_metrics=draft.evaluation_metrics,
                llm_model=model,
                evaluation_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
                evidence=self._build_evidence_records(draft, context),
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, evaluation.id)
        agent_result.growth_evaluation_id = evaluation.id
        return agent_result

    async def get_evaluation(self, evaluation_id: UUID) -> GrowthEvaluationDetail:
        evaluation = await self._repos.growth_evaluations.get_by_id_with_evidence(evaluation_id)
        if evaluation is None:
            raise NotFoundError("growth_evaluation", evaluation_id)
        return GrowthEvaluationDetail.from_entity(evaluation)

    async def list_evaluations(
        self,
        filters: GrowthEvaluationListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[GrowthEvaluationRead]:
        items = await self._repos.growth_evaluations.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.growth_evaluations.count_filtered(filters)
        return PaginatedResponse[GrowthEvaluationRead](
            items=[GrowthEvaluationRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_evaluation(self, opportunity_id: UUID) -> GrowthEvaluationDetail:
        evaluation = await self._repos.growth_evaluations.get_current_for_opportunity(
            opportunity_id,
        )
        if evaluation is None:
            raise NotFoundError("growth_evaluation", opportunity_id)
        loaded = await self._repos.growth_evaluations.get_by_id_with_evidence(evaluation.id)
        assert loaded is not None
        return GrowthEvaluationDetail.from_entity(loaded)

    async def list_history(self, opportunity_id: UUID) -> list[GrowthEvaluationRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        items = await self._repos.growth_evaluations.list_for_opportunity(opportunity_id)
        return [GrowthEvaluationRead.from_entity(item) for item in items]

    @staticmethod
    def _build_context(opportunity) -> OpportunityGrowthContext:
        complaint_evidence = [
            ComplaintEvidenceItem(
                index=index,
                complaint_id=complaint.id,
                signal_id=complaint.signal.id,
                summary=complaint.summary,
                verbatim_quote=complaint.verbatim_quote,
                severity=complaint.severity,
                product_mentions=list(complaint.product_mentions or []),
            )
            for index, complaint in enumerate(opportunity.complaints)
        ]

        return OpportunityGrowthContext(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            problem_statement=opportunity.problem_statement,
            target_user=opportunity.target_user,
            frequency_signal=opportunity.frequency_signal,
            existing_alternatives=opportunity.existing_alternatives,
            gap=opportunity.gap,
            confidence_score=opportunity.confidence_score,
            complaint_evidence=complaint_evidence,
        )

    @staticmethod
    def _build_evidence_records(draft, context: OpportunityGrowthContext):
        items: list[GrowthEvaluationEvidenceCreate] = []
        for evidence in draft.supporting_evidence:
            complaint_id = None
            signal_id = None

            if evidence.complaint_index is not None:
                item = context.complaint_evidence[evidence.complaint_index]
                complaint_id = item.complaint_id
                signal_id = item.signal_id

            items.append(
                GrowthEvaluationEvidenceCreate(
                    evidence_type=evidence.evidence_type,
                    excerpt=evidence.excerpt,
                    source_reference=evidence.source_reference,
                    url=None,
                    supports_conclusion=evidence.supports_conclusion,
                    confidence=evidence.confidence,
                    complaint_id=complaint_id,
                    signal_id=signal_id,
                )
            )
        return items

    async def _persist_eval_logs(
        self,
        opportunity_id: UUID,
        agent_result: GrowthStrategyResult,
        evaluation_id: UUID,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.growth_strategy_model,
            agent_result=agent_result,
            eval_metadata_extra={
                "growth_evaluation_id": str(evaluation_id),
                "evaluation_metrics": agent_result.draft.evaluation_metrics
                if agent_result.draft
                else None,
            },
        )

    @staticmethod
    def _last_model(agent_result: GrowthStrategyResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
