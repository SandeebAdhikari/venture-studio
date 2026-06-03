"""Orchestrates competitor intelligence analysis for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.competitor_intelligence.graph import GRAPH_NAME, CompetitorIntelligenceAgent
from app.agents.competitor_intelligence.llm_client import (
    CompetitorIntelligenceLLMClient,
    OpenAICompetitorIntelligenceClient,
)
from app.agents.competitor_intelligence.schemas import (
    CompetitorAnalysisBatchResult,
    CompetitorAnalysisResult,
    OpportunityCompetitorContext,
)
from app.config import Settings, get_settings
from app.db.enums import CompetitorAnalysisStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.competitor_analysis import (
    CompetitorAnalysisCreate,
    CompetitorAnalysisDetail,
    CompetitorAnalysisRead,
    CompetitorProfileCreate,
)
from app.schemas.filters import CompetitorAnalysisListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class CompetitorIntelligenceService:
    """Analyzes competitors for generated opportunities."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: CompetitorIntelligenceLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: CompetitorIntelligenceAgent | None = None

    def _get_agent(self) -> CompetitorIntelligenceAgent:
        if self._agent is None:
            client = self._llm_client or OpenAICompetitorIntelligenceClient(self._settings)
            self._agent = CompetitorIntelligenceAgent(
                client,
                self._settings,
                budget_service=self._budget,
            )
        return self._agent

    async def analyze_pending(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> CompetitorAnalysisBatchResult:
        batch_size = limit or self._settings.competitor_batch_size
        if force:
            opportunity_ids = await self._repos.competitor_analyses.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = (
                await self._repos.competitor_analyses.list_opportunity_ids_without_analysis(
                    limit=batch_size,
                )
            )

        batch_result = CompetitorAnalysisBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.analyze_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Competitor intelligence batch complete",
            extra={
                "opportunities_found": batch_result.opportunities_found,
                "completed": batch_result.completed,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def analyze_opportunity(
        self,
        opportunity_id: UUID,
        *,
        force: bool = False,
    ) -> CompetitorAnalysisResult:
        if not force:
            existing = await self._repos.competitor_analyses.get_current_for_opportunity(
                opportunity_id,
            )
            if existing is not None and existing.status == CompetitorAnalysisStatus.COMPLETED.value:
                return CompetitorAnalysisResult(
                    opportunity_id=opportunity_id,
                    competitor_analysis_id=existing.id,
                    status="skipped",
                    skip_reason="already_analyzed",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            return agent_result

        model = self._last_model(agent_result) or self._settings.competitor_model
        draft = agent_result.draft
        profiles = [
            CompetitorProfileCreate(
                name=profile.name,
                positioning=profile.positioning,
                pricing_model=profile.pricing.model_dump(),
                strengths=profile.strengths,
                weaknesses=profile.weaknesses,
                customer_complaints=[item.model_dump() for item in profile.customer_complaints],
                review_sentiment=profile.review_sentiment,
                sentiment_score=profile.sentiment_score,
                source_basis=profile.source_basis,
            )
            for profile in draft.competitors
        ]
        analysis = await self._repos.competitor_analyses.create(
            CompetitorAnalysisCreate(
                opportunity_id=opportunity_id,
                status=CompetitorAnalysisStatus.COMPLETED,
                competitive_gaps=[gap.model_dump() for gap in draft.competitive_gaps],
                executive_summary=draft.executive_summary,
                evaluation_metrics=draft.evaluation_metrics,
                llm_model=model,
                analysis_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
                profiles=profiles,
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, analysis.id)
        agent_result.competitor_analysis_id = analysis.id
        return agent_result

    async def get_analysis(self, analysis_id: UUID) -> CompetitorAnalysisDetail:
        analysis = await self._repos.competitor_analyses.get_by_id_with_profiles(analysis_id)
        if analysis is None:
            raise NotFoundError("competitor_analysis", analysis_id)
        return CompetitorAnalysisDetail.from_entity(analysis)

    async def list_analyses(
        self,
        filters: CompetitorAnalysisListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[CompetitorAnalysisRead]:
        items = await self._repos.competitor_analyses.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.competitor_analyses.count_filtered(filters)
        return PaginatedResponse[CompetitorAnalysisRead](
            items=[CompetitorAnalysisRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_analysis(self, opportunity_id: UUID) -> CompetitorAnalysisDetail:
        analysis = await self._repos.competitor_analyses.get_current_for_opportunity(
            opportunity_id,
        )
        if analysis is None:
            raise NotFoundError("competitor_analysis", opportunity_id)
        analysis = await self._repos.competitor_analyses.get_by_id_with_profiles(analysis.id)
        assert analysis is not None
        return CompetitorAnalysisDetail.from_entity(analysis)

    async def list_history(self, opportunity_id: UUID) -> list[CompetitorAnalysisRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        analyses = await self._repos.competitor_analyses.list_for_opportunity(opportunity_id)
        return [CompetitorAnalysisRead.from_entity(item) for item in analyses]

    async def _persist_eval_logs(
        self,
        opportunity_id: UUID,
        agent_result: CompetitorAnalysisResult,
        analysis_id: UUID,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.competitor_model,
            agent_result=agent_result,
            eval_metadata_extra={
                "competitor_analysis_id": str(analysis_id),
                "evaluation_metrics": agent_result.draft.evaluation_metrics
                if agent_result.draft
                else None,
            },
        )

    @staticmethod
    def _build_context(opportunity) -> OpportunityCompetitorContext:
        product_mentions = sorted(
            {
                product
                for complaint in opportunity.complaints
                for product in (complaint.product_mentions or [])
                if product.strip()
            }
        )
        complaint_summaries = [complaint.summary for complaint in opportunity.complaints]

        return OpportunityCompetitorContext(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            problem_statement=opportunity.problem_statement,
            target_user=opportunity.target_user,
            existing_alternatives=opportunity.existing_alternatives,
            gap=opportunity.gap,
            confidence_score=opportunity.confidence_score,
            known_products=product_mentions,
            complaint_summaries=complaint_summaries,
            product_mentions=product_mentions,
        )

    @staticmethod
    def _last_model(agent_result: CompetitorAnalysisResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
