"""Orchestrates customer demand research for opportunities."""

from uuid import UUID

from app.agents.customer_research.graph import GRAPH_NAME, CustomerResearchAgent
from app.agents.customer_research.llm_client import (
    CustomerResearchLLMClient,
    OpenAICustomerResearchClient,
)
from app.agents.customer_research.schemas import (
    ComplaintEvidenceItem,
    CustomerResearchBatchResult,
    CustomerResearchResult,
    OpportunityCustomerContext,
)
from app.config import Settings, get_settings
from app.db.enums import CustomerResearchStatus, SourceType
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.customer_research import (
    CustomerResearchCreate,
    CustomerResearchDetail,
    CustomerResearchEvidenceCreate,
    CustomerResearchRead,
)
from app.schemas.filters import CustomerResearchListFilter
from app.schemas.pagination import PaginatedResponse, PaginationParams

logger = get_logger(__name__)

_SOURCE_TO_EVIDENCE: dict[str, str] = {
    SourceType.REDDIT.value: "forum",
    SourceType.HN_ALGOLIA.value: "discussion",
    SourceType.RSS.value: "social",
}


class CustomerResearchService:
    """Researches whether customers care about an opportunity's problem."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: CustomerResearchLLMClient | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._agent: CustomerResearchAgent | None = None

    def _get_agent(self) -> CustomerResearchAgent:
        if self._agent is None:
            client = self._llm_client or OpenAICustomerResearchClient(self._settings)
            self._agent = CustomerResearchAgent(client, self._settings)
        return self._agent

    async def research_pending(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
    ) -> CustomerResearchBatchResult:
        batch_size = limit or self._settings.customer_research_batch_size
        if force:
            opportunity_ids = await self._repos.customer_research.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = (
                await self._repos.customer_research.list_opportunity_ids_without_research(
                    limit=batch_size,
                )
            )

        batch_result = CustomerResearchBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.research_opportunity(opportunity_id, force=force)
            batch_result.add(item)

        logger.info(
            "Customer research batch complete",
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
    ) -> CustomerResearchResult:
        if not force:
            existing = await self._repos.customer_research.get_current_for_opportunity(
                opportunity_id,
            )
            if existing is not None and existing.status == CustomerResearchStatus.COMPLETED.value:
                return CustomerResearchResult(
                    opportunity_id=opportunity_id,
                    customer_research_id=existing.id,
                    status="skipped",
                    skip_reason="already_researched",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            return agent_result

        model = self._last_model(agent_result) or self._settings.customer_research_model
        draft = agent_result.draft
        evidence_items = self._build_evidence_records(draft, context)

        research = await self._repos.customer_research.create(
            CustomerResearchCreate(
                opportunity_id=opportunity_id,
                status=CustomerResearchStatus.COMPLETED,
                pain_score=draft.pain_score,
                urgency_score=draft.urgency_score,
                frequency_score=draft.frequency_score,
                customer_sentiment=draft.customer_sentiment,
                sentiment_score=draft.sentiment_score,
                cares_verdict=draft.cares_verdict,
                representative_complaints=[
                    item.model_dump() for item in draft.representative_complaints
                ],
                executive_summary=draft.executive_summary,
                validation_metrics=draft.validation_metrics,
                llm_model=model,
                research_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                },
                evidence=evidence_items,
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, research.id)
        agent_result.customer_research_id = research.id
        return agent_result

    async def get_research(self, research_id: UUID) -> CustomerResearchDetail:
        research = await self._repos.customer_research.get_by_id_with_evidence(research_id)
        if research is None:
            raise NotFoundError("customer_research", research_id)
        return CustomerResearchDetail.from_entity(research)

    async def list_research(
        self,
        filters: CustomerResearchListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[CustomerResearchRead]:
        items = await self._repos.customer_research.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.customer_research.count_filtered(filters)
        return PaginatedResponse[CustomerResearchRead](
            items=[CustomerResearchRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_research(self, opportunity_id: UUID) -> CustomerResearchDetail:
        research = await self._repos.customer_research.get_current_for_opportunity(opportunity_id)
        if research is None:
            raise NotFoundError("customer_research", opportunity_id)
        loaded = await self._repos.customer_research.get_by_id_with_evidence(research.id)
        assert loaded is not None
        return CustomerResearchDetail.from_entity(loaded)

    async def list_history(self, opportunity_id: UUID) -> list[CustomerResearchRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        items = await self._repos.customer_research.list_for_opportunity(opportunity_id)
        return [CustomerResearchRead.from_entity(item) for item in items]

    async def _persist_eval_logs(
        self,
        opportunity_id: UUID,
        agent_result: CustomerResearchResult,
        research_id: UUID,
    ) -> None:
        for log in agent_result.eval_logs:
            status = "success" if log.get("error") is None else "error"
            await self._repos.llm_calls.log_agent_call(
                entity_type="opportunity",
                entity_id=opportunity_id,
                graph_name=GRAPH_NAME,
                model=log.get("model", self._settings.customer_research_model),
                attempt=int(log.get("attempt", 1)),
                prompt_tokens=int(log.get("prompt_tokens", 0)),
                completion_tokens=int(log.get("completion_tokens", 0)),
                latency_ms=log.get("latency_ms"),
                cost_usd=log.get("cost_usd"),
                status=status,
                error_detail=log.get("error"),
                eval_metadata={
                    "parsed": log.get("parsed"),
                    "raw_text": log.get("raw_text"),
                    "agent_status": agent_result.status,
                    "attempts": agent_result.attempts,
                    "customer_research_id": str(research_id),
                    "validation_metrics": agent_result.draft.validation_metrics
                    if agent_result.draft
                    else None,
                },
            )

    @staticmethod
    def _build_context(opportunity) -> OpportunityCustomerContext:
        evidence: list[ComplaintEvidenceItem] = []
        for index, complaint in enumerate(opportunity.complaints):
            signal = complaint.signal
            source = signal.source
            source_type = _SOURCE_TO_EVIDENCE.get(source.source_type, "discussion")
            evidence.append(
                ComplaintEvidenceItem(
                    index=index,
                    complaint_id=complaint.id,
                    signal_id=signal.id,
                    summary=complaint.summary,
                    verbatim_quote=complaint.verbatim_quote,
                    severity=complaint.severity,
                    source_type=source_type,
                    source_name=source.name,
                    url=signal.url,
                )
            )

        return OpportunityCustomerContext(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            problem_statement=opportunity.problem_statement,
            target_user=opportunity.target_user,
            frequency_signal=opportunity.frequency_signal,
            gap=opportunity.gap,
            confidence_score=opportunity.confidence_score,
            complaint_evidence=evidence,
        )

    @staticmethod
    def _build_evidence_records(draft, context: OpportunityCustomerContext):
        items: list[CustomerResearchEvidenceCreate] = []
        for evidence in draft.supporting_evidence:
            complaint_id = None
            signal_id = None
            url = None
            if evidence.complaint_index is not None:
                item = context.complaint_evidence[evidence.complaint_index]
                complaint_id = item.complaint_id
                signal_id = item.signal_id
                url = item.url
            items.append(
                CustomerResearchEvidenceCreate(
                    evidence_type=evidence.evidence_type,
                    excerpt=evidence.excerpt,
                    source_reference=evidence.source_reference,
                    url=url,
                    supports_conclusion=evidence.supports_conclusion,
                    confidence=evidence.confidence,
                    complaint_id=complaint_id,
                    signal_id=signal_id,
                )
            )
        return items

    @staticmethod
    def _last_model(agent_result: CustomerResearchResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
