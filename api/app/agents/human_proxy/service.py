"""Orchestrates human proxy founder-fit evaluation for opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.human_proxy.graph import GRAPH_NAME, HumanProxyAgent
from app.agents.human_proxy.llm_client import HumanProxyLLMClient, OpenAIHumanProxyClient
from app.agents.human_proxy.schemas import (
    ComplaintEvidenceItem,
    FounderProfileContext,
    HumanProxyBatchResult,
    HumanProxyResult,
    OpportunityProxyContext,
)
from app.config import Settings, get_settings
from app.db.enums import HumanProxyEvaluationStatus
from app.db.models.founder_profile import FounderProfile
from app.exceptions import NotFoundError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import HumanProxyEvaluationListFilter
from app.schemas.founder_profile import FounderProfileCreate, FounderProfileRead
from app.schemas.human_proxy_evaluation import (
    HumanProxyEvaluationCreate,
    HumanProxyEvaluationDetail,
    HumanProxyEvaluationEvidenceCreate,
    HumanProxyEvaluationRead,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class HumanProxyService:
    """Ranks opportunities according to a founder profile."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: HumanProxyLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: HumanProxyAgent | None = None

    def _get_agent(self) -> HumanProxyAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIHumanProxyClient(self._settings)
            self._agent = HumanProxyAgent(
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
        founder_profile_id: UUID | None = None,
    ) -> HumanProxyBatchResult:
        profile = await self._resolve_profile(founder_profile_id)
        batch_size = limit or self._settings.human_proxy_batch_size
        if force:
            opportunity_ids = await self._repos.human_proxy_evaluations.list_opportunity_ids(
                limit=batch_size,
            )
        else:
            opportunity_ids = (
                await self._repos.human_proxy_evaluations.list_opportunity_ids_without_evaluation(
                    founder_profile_id=profile.id,
                    limit=batch_size,
                )
            )

        batch_result = HumanProxyBatchResult(opportunities_found=len(opportunity_ids))
        for opportunity_id in opportunity_ids:
            item = await self.evaluate_opportunity(
                opportunity_id,
                founder_profile_id=profile.id,
                force=force,
            )
            batch_result.add(item)

        logger.info(
            "Human proxy batch complete",
            extra={
                "founder_profile_id": str(profile.id),
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
        founder_profile_id: UUID | None = None,
        force: bool = False,
    ) -> HumanProxyResult:
        profile = await self._resolve_profile(founder_profile_id)

        if not force:
            existing = await self._repos.human_proxy_evaluations.get_current_for_opportunity(
                opportunity_id,
                founder_profile_id=profile.id,
            )
            if (
                existing is not None
                and existing.status == HumanProxyEvaluationStatus.COMPLETED.value
            ):
                return HumanProxyResult(
                    opportunity_id=opportunity_id,
                    founder_profile_id=profile.id,
                    human_proxy_evaluation_id=existing.id,
                    status="skipped",
                    skip_reason="already_evaluated",
                )

        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        context = self._build_context(opportunity, profile)
        agent_result = await self._get_agent().run(context)

        if agent_result.status != "completed" or agent_result.draft is None:
            await self._persist_eval_logs(opportunity_id, agent_result)
            return agent_result

        model = self._last_model(agent_result) or self._settings.human_proxy_model
        draft = agent_result.draft
        evaluation = await self._repos.human_proxy_evaluations.create(
            HumanProxyEvaluationCreate(
                opportunity_id=opportunity_id,
                founder_profile_id=profile.id,
                status=HumanProxyEvaluationStatus.COMPLETED,
                founder_fit_score=draft.founder_fit_score,
                feasibility_score=draft.feasibility_score,
                recommendation=draft.recommendation,
                founder_fit_analysis=draft.founder_fit_analysis.model_dump(),
                implementation_feasibility=draft.implementation_feasibility.model_dump(),
                learning_curve=draft.learning_curve.model_dump(),
                execution_complexity=draft.execution_complexity.model_dump(),
                capital_requirements=draft.capital_requirements.model_dump(),
                executive_summary=draft.executive_summary,
                evaluation_metrics=draft.evaluation_metrics,
                llm_model=model,
                proxy_metadata={
                    "graph_name": GRAPH_NAME,
                    "attempts": agent_result.attempts,
                    "agent_status": agent_result.status,
                    "founder_profile_name": profile.name,
                    "scale_metadata": draft.scale_metadata,
                },
                evidence=self._build_evidence_records(draft, context),
            )
        )

        await self._persist_eval_logs(opportunity_id, agent_result, evaluation.id)
        agent_result.human_proxy_evaluation_id = evaluation.id
        return agent_result

    async def get_evaluation(self, evaluation_id: UUID) -> HumanProxyEvaluationDetail:
        evaluation = await self._repos.human_proxy_evaluations.get_by_id_with_evidence(
            evaluation_id
        )
        if evaluation is None:
            raise NotFoundError("human_proxy_evaluation", evaluation_id)
        return HumanProxyEvaluationDetail.from_entity(evaluation)

    async def list_evaluations(
        self,
        filters: HumanProxyEvaluationListFilter,
        pagination: PaginationParams,
    ) -> PaginatedResponse[HumanProxyEvaluationRead]:
        items = await self._repos.human_proxy_evaluations.list_filtered(
            filters,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self._repos.human_proxy_evaluations.count_filtered(filters)
        return PaginatedResponse[HumanProxyEvaluationRead](
            items=[HumanProxyEvaluationRead.from_entity(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_current_evaluation(
        self,
        opportunity_id: UUID,
        *,
        founder_profile_id: UUID | None = None,
    ) -> HumanProxyEvaluationDetail:
        profile = await self._resolve_profile(founder_profile_id)
        evaluation = await self._repos.human_proxy_evaluations.get_current_for_opportunity(
            opportunity_id,
            founder_profile_id=profile.id,
        )
        if evaluation is None:
            raise NotFoundError("human_proxy_evaluation", opportunity_id)
        loaded = await self._repos.human_proxy_evaluations.get_by_id_with_evidence(evaluation.id)
        assert loaded is not None
        return HumanProxyEvaluationDetail.from_entity(loaded)

    async def list_history(
        self,
        opportunity_id: UUID,
        *,
        founder_profile_id: UUID | None = None,
    ) -> list[HumanProxyEvaluationRead]:
        opportunity = await self._repos.opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)
        profile = await self._resolve_profile(founder_profile_id)
        items = await self._repos.human_proxy_evaluations.list_for_opportunity(
            opportunity_id,
            founder_profile_id=profile.id,
        )
        return [HumanProxyEvaluationRead.from_entity(item) for item in items]

    async def list_profiles(self) -> list[FounderProfileRead]:
        items = await self._repos.founder_profiles.list_active()
        return [FounderProfileRead.from_entity(item) for item in items]

    async def get_profile(self, profile_id: UUID) -> FounderProfileRead:
        profile = await self._repos.founder_profiles.get_by_id(profile_id)
        if profile is None:
            raise NotFoundError("founder_profile", profile_id)
        return FounderProfileRead.from_entity(profile)

    async def create_profile(self, data: FounderProfileCreate) -> FounderProfileRead:
        profile = await self._repos.founder_profiles.create(data)
        return FounderProfileRead.from_entity(profile)

    async def _resolve_profile(self, founder_profile_id: UUID | None) -> FounderProfile:
        if founder_profile_id is not None:
            profile = await self._repos.founder_profiles.get_by_id(founder_profile_id)
            if profile is None:
                raise NotFoundError("founder_profile", founder_profile_id)
            if not profile.is_active:
                raise NotFoundError("founder_profile", founder_profile_id)
            return profile

        profile = await self._repos.founder_profiles.get_default()
        if profile is None:
            raise NotFoundError("founder_profile", "default")
        return profile

    @staticmethod
    def _build_context(opportunity, profile: FounderProfile) -> OpportunityProxyContext:
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

        return OpportunityProxyContext(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            problem_statement=opportunity.problem_statement,
            target_user=opportunity.target_user,
            frequency_signal=opportunity.frequency_signal,
            existing_alternatives=opportunity.existing_alternatives,
            gap=opportunity.gap,
            confidence_score=opportunity.confidence_score,
            founder_profile=FounderProfileContext(
                founder_profile_id=profile.id,
                name=profile.name,
                skills=list(profile.skills or []),
                constraints=dict(profile.constraints or {}),
                description=profile.description,
            ),
            complaint_evidence=complaint_evidence,
        )

    @staticmethod
    def _build_evidence_records(draft, context: OpportunityProxyContext):
        items: list[HumanProxyEvaluationEvidenceCreate] = []
        for evidence in draft.supporting_evidence:
            complaint_id = None
            signal_id = None

            if evidence.complaint_index is not None:
                item = context.complaint_evidence[evidence.complaint_index]
                complaint_id = item.complaint_id
                signal_id = item.signal_id

            items.append(
                HumanProxyEvaluationEvidenceCreate(
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
        agent_result: HumanProxyResult,
        evaluation_id: UUID | None = None,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        extra: dict[str, object] = {}
        if evaluation_id is not None:
            extra["human_proxy_evaluation_id"] = str(evaluation_id)
        if agent_result.error:
            extra["failure_error"] = agent_result.error
        if agent_result.draft is not None:
            extra["evaluation_metrics"] = agent_result.draft.evaluation_metrics

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="opportunity",
            entity_id=opportunity_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.human_proxy_model,
            agent_result=agent_result,
            eval_metadata_extra=extra or None,
        )

    @staticmethod
    def _last_model(agent_result: HumanProxyResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
