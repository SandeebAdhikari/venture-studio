"""Orchestrates go-to-market planning for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.go_to_market.graph import GRAPH_NAME, GoToMarketAgent
from app.agents.go_to_market.llm_client import GoToMarketLLMClient, OpenAIGoToMarketClient
from app.agents.go_to_market.schemas import (
    ComplaintEvidenceItem,
    GoToMarketBatchResult,
    GoToMarketResult,
    OpportunityGTMContext,
)
from app.config import Settings, get_settings
from app.db.enums import GTMPlanStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import GTMPlanListFilter
from app.schemas.gtm_plan import (
    GTMPlanCreate,
    GTMPlanDetail,
    GTMPlanEvidenceCreate,
    GTMPlanRead,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class GoToMarketService:
    """Generates customer acquisition strategies for opportunities."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: GoToMarketLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: GoToMarketAgent | None = None

    def _get_agent(self) -> GoToMarketAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIGoToMarketClient(self._settings)
            self._agent = GoToMarketAgent(
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
    ) -> GoToMarketBatchResult:
        batch_size = limit or self._settings.go_to_market_batch_size
        if force:
            opportunity_ids = await self._repos.gtm_plans.list_opportunity_ids(limit=batch_size)
        else:
            opportunity_ids = await self._repos.gtm_plans.list_opportunity_ids_without_plan(
                limit=batch_size,
            )

        batch_result = GoToMarketBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.plan_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Go-to-market batch complete",
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
    ) -> GoToMarketResult:
        if not force:
            existing = await self._repos.gtm_plans.get_current_for_opportunity(opportunity_id)
            if existing is not None and existing.status == GTMPlanStatus.COMPLETED.value:
                return GoToMarketResult(
                    opportunity_id=opportunity_id,
                    gtm_plan_id=existing.id,
                    status="skipped",
                    skip_reason="already_planned",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            await self._persist_eval_logs(opportunity_id, agent_result)
            return agent_result

        model = self._last_model(agent_result) or self._settings.go_to_market_model
        draft = agent_result.draft
        plan = await self._repos.gtm_plans.create(
            GTMPlanCreate(
                opportunity_id=opportunity_id,
                status=GTMPlanStatus.COMPLETED,
                ideal_customer_profile=draft.ideal_customer_profile.model_dump(),
                customer_personas=[item.model_dump() for item in draft.customer_personas],
                acquisition_channels=[item.model_dump() for item in draft.acquisition_channels],
                outreach_strategy=draft.outreach_strategy.model_dump(),
                content_strategy=draft.content_strategy.model_dump(),
                seo_opportunities=[item.model_dump() for item in draft.seo_opportunities],
                partnerships=[item.model_dump() for item in draft.partnerships],
                first_100_customers_plan=draft.first_100_customers_plan.model_dump(),
                gtm_report=draft.gtm_report,
                acquisition_roadmap=draft.acquisition_roadmap,
                estimated_cac_usd=draft.estimated_cac_usd,
                confidence_score=draft.confidence_score,
                ranking_metrics=draft.ranking_metrics,
                llm_model=model,
                gtm_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
                evidence=self._build_evidence_records(draft, context),
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, plan.id)
        agent_result.gtm_plan_id = plan.id
        return agent_result

    async def get_plan(self, plan_id: UUID) -> GTMPlanDetail:
        plan = await self._repos.gtm_plans.get_by_id_with_evidence(plan_id)
        if plan is None:
            raise NotFoundError("gtm_plan", plan_id)
        return GTMPlanDetail.from_entity(plan)

    async def list_plans(
        self,
        filters: GTMPlanListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[GTMPlanRead]:
        items = await self._repos.gtm_plans.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.gtm_plans.count_filtered(filters)
        return PaginatedResponse[GTMPlanRead](
            items=[GTMPlanRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_plan(self, opportunity_id: UUID) -> GTMPlanDetail:
        plan = await self._repos.gtm_plans.get_current_for_opportunity(opportunity_id)
        if plan is None:
            raise NotFoundError("gtm_plan", opportunity_id)
        loaded = await self._repos.gtm_plans.get_by_id_with_evidence(plan.id)
        assert loaded is not None
        return GTMPlanDetail.from_entity(loaded)

    async def list_history(self, opportunity_id: UUID) -> list[GTMPlanRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        items = await self._repos.gtm_plans.list_for_opportunity(opportunity_id)
        return [GTMPlanRead.from_entity(item) for item in items]

    @staticmethod
    def _build_context(opportunity) -> OpportunityGTMContext:
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

        return OpportunityGTMContext(
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
    def _build_evidence_records(draft, context: OpportunityGTMContext):
        items: list[GTMPlanEvidenceCreate] = []
        for evidence in draft.supporting_evidence:
            complaint_id = None
            signal_id = None

            if evidence.complaint_index is not None:
                item = context.complaint_evidence[evidence.complaint_index]
                complaint_id = item.complaint_id
                signal_id = item.signal_id

            items.append(
                GTMPlanEvidenceCreate(
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
        agent_result: GoToMarketResult,
        plan_id: UUID | None = None,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        extra: dict[str, object] = {}
        if plan_id is not None:
            extra["gtm_plan_id"] = str(plan_id)
        if agent_result.error:
            extra["failure_error"] = agent_result.error

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.go_to_market_model,
            agent_result=agent_result,
            eval_metadata_extra=extra or None,
        )

    @staticmethod
    def _last_model(agent_result: GoToMarketResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
