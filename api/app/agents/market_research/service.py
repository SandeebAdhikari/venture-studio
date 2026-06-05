"""Orchestrates market intelligence research for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.market_research.graph import GRAPH_NAME, MarketResearchAgent
from app.agents.market_research.llm_client import (
    MarketResearchLLMClient,
    OpenAIMarketResearchClient,
)
from app.agents.market_research.schemas import (
    MarketResearchBatchResult,
    MarketResearchResult,
    OpportunityResearchContext,
)
from app.config import Settings, get_settings
from app.db.enums import MarketResearchStatus
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import MarketBriefListFilter
from app.schemas.market_brief import MarketBriefCreate, MarketBriefRead
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class MarketResearchService:
    """Researches market intelligence for generated opportunities."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: MarketResearchLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: MarketResearchAgent | None = None

    def _get_agent(self) -> MarketResearchAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIMarketResearchClient(self._settings)
            self._agent = MarketResearchAgent(
                client,
                self._settings,
                budget_service=self._budget,
            )
        return self._agent

    async def research_pending(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> MarketResearchBatchResult:
        batch_size = limit or self._settings.research_batch_size
        if force:
            opportunity_ids = await self._repos.market_briefs.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = await self._repos.market_briefs.list_opportunity_ids_without_research(
                limit=batch_size,
            )

        batch_result = MarketResearchBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.research_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Market research batch complete",
            extra={
                "opportunities_found": batch_result.opportunities_found,
                "completed": batch_result.completed,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def research_opportunity(
        self,
        opportunity_id: UUID,
        *,
        force: bool = False,
    ) -> MarketResearchResult:
        if not force:
            existing = await self._repos.market_briefs.get_current_for_opportunity(opportunity_id)
            if existing is not None and existing.status == MarketResearchStatus.COMPLETED.value:
                return MarketResearchResult(
                    opportunity_id=opportunity_id,
                    market_brief_id=existing.id,
                    status="skipped",
                    skip_reason="already_researched",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            await self._persist_eval_logs(opportunity_id, agent_result)
            return agent_result

        model = self._last_model(agent_result) or self._settings.research_model
        draft = agent_result.draft
        brief = await self._repos.market_briefs.create(
            MarketBriefCreate(
                opportunity_id=opportunity_id,
                status=MarketResearchStatus.COMPLETED,
                market_size_usd=draft.market_size_usd,
                tam_usd=draft.tam_usd,
                sam_usd=draft.sam_usd,
                industry_growth_rate_pct=draft.industry_growth_rate_pct,
                customer_segments=[segment.model_dump() for segment in draft.customer_segments],
                industry_trends=[trend.model_dump() for trend in draft.industry_trends],
                supporting_evidence=[item.model_dump() for item in draft.supporting_evidence],
                executive_summary=draft.executive_summary,
                llm_model=model,
                research_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result)
        agent_result.market_brief_id = brief.id
        return agent_result

    async def get_brief(self, brief_id: UUID) -> MarketBriefRead:
        brief = await self._repos.market_briefs.get_by_id(brief_id)
        if brief is None:
            raise NotFoundError("market_brief", brief_id)
        return MarketBriefRead.model_validate(brief)

    async def list_briefs(
        self,
        filters: MarketBriefListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[MarketBriefRead]:
        items = await self._repos.market_briefs.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.market_briefs.count_filtered(filters)
        return PaginatedResponse[MarketBriefRead](
            items=[MarketBriefRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_brief(self, opportunity_id: UUID) -> MarketBriefRead:
        brief = await self._repos.market_briefs.get_current_for_opportunity(opportunity_id)
        if brief is None:
            raise NotFoundError("market_brief", opportunity_id)
        return MarketBriefRead.model_validate(brief)

    async def list_history(self, opportunity_id: UUID) -> list[MarketBriefRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        briefs = await self._repos.market_briefs.list_for_opportunity(opportunity_id)
        return [MarketBriefRead.model_validate(item) for item in briefs]

    async def _persist_eval_logs(
        self,
        opportunity_id: UUID,
        agent_result: MarketResearchResult,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.research_model,
            agent_result=agent_result,
            eval_metadata_extra={
                "market_brief_id": str(agent_result.market_brief_id)
                if agent_result.market_brief_id
                else None,
                "agent_validation_errors": agent_result.validation_errors or None,
            },
        )

    @staticmethod
    def _build_context(opportunity) -> OpportunityResearchContext:
        domain_codes = sorted({complaint.domain.code for complaint in opportunity.complaints})
        category_codes = sorted({complaint.category.code for complaint in opportunity.complaints})
        persona_codes = sorted({complaint.persona.code for complaint in opportunity.complaints})
        complaint_summaries = [complaint.summary for complaint in opportunity.complaints]

        return OpportunityResearchContext(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            problem_statement=opportunity.problem_statement,
            target_user=opportunity.target_user,
            frequency_signal=opportunity.frequency_signal,
            existing_alternatives=opportunity.existing_alternatives,
            gap=opportunity.gap,
            confidence_score=opportunity.confidence_score,
            domain_codes=domain_codes,
            category_codes=category_codes,
            persona_codes=persona_codes,
            complaint_summaries=complaint_summaries,
        )

    @staticmethod
    def _last_model(agent_result: MarketResearchResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
