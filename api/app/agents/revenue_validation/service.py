"""Orchestrates revenue validation for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.revenue_validation.graph import GRAPH_NAME, RevenueValidationAgent
from app.agents.revenue_validation.llm_client import (
    OpenAIRevenueValidationClient,
    RevenueValidationLLMClient,
)
from app.agents.revenue_validation.schemas import (
    ComplaintEvidenceItem,
    CompetitorPricingContext,
    OpportunityRevenueContext,
    RevenueValidationBatchResult,
    RevenueValidationResult,
)
from app.config import Settings, get_settings
from app.db.enums import RevenueValidationStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import RevenueValidationListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.revenue_validation import (
    RevenueValidationCreate,
    RevenueValidationDetail,
    RevenueValidationEvidenceCreate,
    RevenueValidationRead,
)

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class RevenueValidationService:
    """Validates whether customers are willing to pay for an opportunity."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: RevenueValidationLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: RevenueValidationAgent | None = None

    def _get_agent(self) -> RevenueValidationAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIRevenueValidationClient(self._settings)
            self._agent = RevenueValidationAgent(
                client,
                self._settings,
                budget_service=self._budget,
            )
        return self._agent

    async def validate_pending(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> RevenueValidationBatchResult:
        batch_size = limit or self._settings.revenue_validation_batch_size
        if force:
            opportunity_ids = await self._repos.revenue_validations.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = (
                await self._repos.revenue_validations.list_opportunity_ids_without_validation(
                    limit=batch_size,
                )
            )

        batch_result = RevenueValidationBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.validate_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Revenue validation batch complete",
            extra={
                "opportunities_found": batch_result.opportunities_found,
                "completed": batch_result.completed,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def validate_opportunity(
        self,
        opportunity_id: UUID,
        *,
        force: bool = False,
    ) -> RevenueValidationResult:
        if not force:
            existing = await self._repos.revenue_validations.get_current_for_opportunity(
                opportunity_id,
            )
            if existing is not None and existing.status == RevenueValidationStatus.COMPLETED.value:
                return RevenueValidationResult(
                    opportunity_id=opportunity_id,
                    revenue_validation_id=existing.id,
                    status="skipped",
                    skip_reason="already_validated",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = await self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            return agent_result

        model = self._last_model(agent_result) or self._settings.revenue_validation_model
        draft = agent_result.draft
        validation = await self._repos.revenue_validations.create(
            RevenueValidationCreate(
                opportunity_id=opportunity_id,
                status=RevenueValidationStatus.COMPLETED,
                willingness_to_pay_score=draft.willingness_to_pay_score,
                revenue_confidence_score=draft.revenue_confidence_score,
                pricing_recommendations=[
                    item.model_dump() for item in draft.pricing_recommendations
                ],
                buyer_profiles=[item.model_dump() for item in draft.buyer_profiles],
                executive_summary=draft.executive_summary,
                evaluation_metrics=draft.evaluation_metrics,
                llm_model=model,
                validation_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
                evidence=self._build_evidence_records(draft, context),
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, validation.id)
        agent_result.revenue_validation_id = validation.id
        return agent_result

    async def get_validation(self, validation_id: UUID) -> RevenueValidationDetail:
        validation = await self._repos.revenue_validations.get_by_id_with_evidence(validation_id)
        if validation is None:
            raise NotFoundError("revenue_validation", validation_id)
        return RevenueValidationDetail.from_entity(validation)

    async def list_validations(
        self,
        filters: RevenueValidationListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[RevenueValidationRead]:
        items = await self._repos.revenue_validations.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.revenue_validations.count_filtered(filters)
        return PaginatedResponse[RevenueValidationRead](
            items=[RevenueValidationRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_validation(self, opportunity_id: UUID) -> RevenueValidationDetail:
        validation = await self._repos.revenue_validations.get_current_for_opportunity(
            opportunity_id,
        )
        if validation is None:
            raise NotFoundError("revenue_validation", opportunity_id)
        loaded = await self._repos.revenue_validations.get_by_id_with_evidence(validation.id)
        assert loaded is not None
        return RevenueValidationDetail.from_entity(loaded)

    async def list_history(self, opportunity_id: UUID) -> list[RevenueValidationRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        items = await self._repos.revenue_validations.list_for_opportunity(opportunity_id)
        return [RevenueValidationRead.from_entity(item) for item in items]

    async def _build_context(self, opportunity) -> OpportunityRevenueContext:
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

        competitor_pricing: list[CompetitorPricingContext] = []
        analysis = await self._repos.competitor_analyses.get_current_for_opportunity(
            opportunity.id,
        )
        if analysis is not None:
            loaded = await self._repos.competitor_analyses.get_by_id_with_profiles(analysis.id)
            if loaded is not None:
                competitor_pricing = [
                    CompetitorPricingContext(
                        index=index,
                        competitor_profile_id=profile.id,
                        name=profile.name,
                        pricing_model=profile.pricing_model,
                        positioning=profile.positioning,
                    )
                    for index, profile in enumerate(loaded.profiles)
                ]

        return OpportunityRevenueContext(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            problem_statement=opportunity.problem_statement,
            target_user=opportunity.target_user,
            existing_alternatives=opportunity.existing_alternatives,
            gap=opportunity.gap,
            confidence_score=opportunity.confidence_score,
            complaint_evidence=complaint_evidence,
            competitor_pricing=competitor_pricing,
        )

    @staticmethod
    def _build_evidence_records(draft, context: OpportunityRevenueContext):
        items: list[RevenueValidationEvidenceCreate] = []
        for evidence in draft.supporting_evidence:
            complaint_id = None
            signal_id = None
            competitor_profile_id = None
            url = None

            if evidence.complaint_index is not None:
                item = context.complaint_evidence[evidence.complaint_index]
                complaint_id = item.complaint_id
                signal_id = item.signal_id
            if evidence.competitor_index is not None:
                competitor = context.competitor_pricing[evidence.competitor_index]
                competitor_profile_id = competitor.competitor_profile_id

            items.append(
                RevenueValidationEvidenceCreate(
                    evidence_type=evidence.evidence_type,
                    excerpt=evidence.excerpt,
                    source_reference=evidence.source_reference,
                    url=url,
                    supports_conclusion=evidence.supports_conclusion,
                    confidence=evidence.confidence,
                    complaint_id=complaint_id,
                    signal_id=signal_id,
                    competitor_profile_id=competitor_profile_id,
                )
            )
        return items

    async def _persist_eval_logs(
        self,
        opportunity_id: UUID,
        agent_result: RevenueValidationResult,
        validation_id: UUID,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.revenue_validation_model,
            agent_result=agent_result,
            eval_metadata_extra={
                "revenue_validation_id": str(validation_id),
                "evaluation_metrics": agent_result.draft.evaluation_metrics
                if agent_result.draft
                else None,
            },
        )

    @staticmethod
    def _last_model(agent_result: RevenueValidationResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
