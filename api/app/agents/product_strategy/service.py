"""Orchestrates product strategy planning for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.product_strategy.graph import GRAPH_NAME, ProductStrategyAgent
from app.agents.product_strategy.llm_client import (
    OpenAIProductStrategyClient,
    ProductStrategyLLMClient,
)
from app.agents.product_strategy.schemas import (
    ComplaintEvidenceItem,
    OpportunityPlanningContext,
    ProductStrategyBatchResult,
    ProductStrategyResult,
)
from app.config import Settings, get_settings
from app.db.enums import ProductStrategyStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import ProductStrategyListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product_strategy import (
    ProductStrategyCreate,
    ProductStrategyDetail,
    ProductStrategyEvidenceCreate,
    ProductStrategyRead,
)

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class ProductStrategyService:
    """Converts validated opportunities into product plans."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: ProductStrategyLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: ProductStrategyAgent | None = None

    def _get_agent(self) -> ProductStrategyAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIProductStrategyClient(self._settings)
            self._agent = ProductStrategyAgent(
                client,
                self._settings,
                budget_service=self._budget,
            )
        return self._agent

    async def plan_pending(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> ProductStrategyBatchResult:
        batch_size = limit or self._settings.product_strategy_batch_size
        if force:
            opportunity_ids = await self._repos.product_strategies.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = (
                await self._repos.product_strategies.list_opportunity_ids_without_strategy(
                    limit=batch_size,
                )
            )

        batch_result = ProductStrategyBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.plan_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Product strategy batch complete",
            extra={
                "opportunities_found": batch_result.opportunities_found,
                "completed": batch_result.completed,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def plan_opportunity(
        self,
        opportunity_id: UUID,
        *,
        force: bool = False,
    ) -> ProductStrategyResult:
        if not force:
            existing = await self._repos.product_strategies.get_current_for_opportunity(
                opportunity_id,
            )
            if existing is not None and existing.status == ProductStrategyStatus.COMPLETED.value:
                return ProductStrategyResult(
                    opportunity_id=opportunity_id,
                    product_strategy_id=existing.id,
                    status="skipped",
                    skip_reason="already_planned",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            return agent_result

        model = self._last_model(agent_result) or self._settings.product_strategy_model
        draft = agent_result.draft
        strategy = await self._repos.product_strategies.create(
            ProductStrategyCreate(
                opportunity_id=opportunity_id,
                status=ProductStrategyStatus.COMPLETED,
                mvp_definition=draft.mvp_definition,
                core_features=[item.model_dump() for item in draft.core_features],
                feature_priorities=[item.model_dump() for item in draft.feature_priorities],
                development_phases=[item.model_dump() for item in draft.development_phases],
                estimated_timeline=draft.estimated_timeline.model_dump(),
                technical_risks=[item.model_dump() for item in draft.technical_risks],
                roadmap=draft.roadmap,
                executive_summary=draft.executive_summary,
                planning_metrics=draft.planning_metrics,
                llm_model=model,
                strategy_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
                evidence=self._build_evidence_records(draft, context),
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, strategy.id)
        agent_result.product_strategy_id = strategy.id
        return agent_result

    async def get_strategy(self, strategy_id: UUID) -> ProductStrategyDetail:
        strategy = await self._repos.product_strategies.get_by_id_with_evidence(strategy_id)
        if strategy is None:
            raise NotFoundError("product_strategy", strategy_id)
        return ProductStrategyDetail.from_entity(strategy)

    async def list_strategies(
        self,
        filters: ProductStrategyListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ProductStrategyRead]:
        items = await self._repos.product_strategies.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.product_strategies.count_filtered(filters)
        return PaginatedResponse[ProductStrategyRead](
            items=[ProductStrategyRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_strategy(self, opportunity_id: UUID) -> ProductStrategyDetail:
        strategy = await self._repos.product_strategies.get_current_for_opportunity(
            opportunity_id,
        )
        if strategy is None:
            raise NotFoundError("product_strategy", opportunity_id)
        loaded = await self._repos.product_strategies.get_by_id_with_evidence(strategy.id)
        assert loaded is not None
        return ProductStrategyDetail.from_entity(loaded)

    async def list_history(self, opportunity_id: UUID) -> list[ProductStrategyRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        items = await self._repos.product_strategies.list_for_opportunity(opportunity_id)
        return [ProductStrategyRead.from_entity(item) for item in items]

    @staticmethod
    def _build_context(opportunity) -> OpportunityPlanningContext:
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

        return OpportunityPlanningContext(
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
    def _build_evidence_records(draft, context: OpportunityPlanningContext):
        items: list[ProductStrategyEvidenceCreate] = []
        for evidence in draft.supporting_evidence:
            complaint_id = None
            signal_id = None

            if evidence.complaint_index is not None:
                item = context.complaint_evidence[evidence.complaint_index]
                complaint_id = item.complaint_id
                signal_id = item.signal_id

            items.append(
                ProductStrategyEvidenceCreate(
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
        agent_result: ProductStrategyResult,
        strategy_id: UUID,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.product_strategy_model,
            agent_result=agent_result,
            eval_metadata_extra={"product_strategy_id": str(strategy_id)},
        )

    @staticmethod
    def _last_model(agent_result: ProductStrategyResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
