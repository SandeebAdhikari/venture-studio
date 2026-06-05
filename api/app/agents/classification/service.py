"""Orchestrates signal classification: agent → complaint persistence → audit logs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.agents.classification.graph import GRAPH_NAME, ComplaintClassificationAgent
from app.agents.classification.llm_client import ClassificationLLMClient, OpenAIClassificationClient
from app.agents.classification.schemas import (
    ClassificationAgentResult,
    ClassificationBatchResult,
    RawComplaintText,
)
from app.config import Settings, get_settings
from app.db.enums import SignalProcessingStatus
from app.exceptions import NotFoundError, ValidationError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.complaint import ComplaintCreate

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)


class ComplaintClassificationService:
    """Classifies pending signals into structured complaints."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: ClassificationLLMClient | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._budget = budget_service
        self._agent: ComplaintClassificationAgent | None = None

    def _get_agent(self) -> ComplaintClassificationAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIClassificationClient(self._settings)
            self._agent = ComplaintClassificationAgent(
                client,
                self._settings,
                budget_service=self._budget,
            )
        return self._agent

    async def classify_signal(self, signal_id: UUID) -> ClassificationAgentResult:
        signal = await self._repos.signals.get_by_id(signal_id)
        if signal is None:
            raise NotFoundError("signal", signal_id)

        if signal.processing_status not in {
            SignalProcessingStatus.PENDING.value,
            SignalProcessingStatus.FAILED.value,
        }:
            raise ValidationError(
                f"Signal '{signal_id}' cannot be classified (status={signal.processing_status})"
            )

        existing = await self._repos.complaints.get_by_signal_id(signal_id)
        if existing is not None:
            raise ValidationError(f"Signal '{signal_id}' already has a complaint")

        await self._repos.signals.set_processing_status(signal, SignalProcessingStatus.PROCESSING)

        agent_result = await self._get_agent().run(
            RawComplaintText(
                body=signal.body,
                title=signal.title,
                url=signal.url,
                signal_id=signal.id,
            )
        )

        await self._persist_eval_logs(signal_id, agent_result)
        return await self._finalize_signal(signal, agent_result)

    async def classify_pending(self, *, limit: int | None = None) -> ClassificationBatchResult:
        batch_size = limit or self._settings.classify_batch_size
        pending = await self._repos.signals.list_pending(limit=batch_size)
        batch_result = ClassificationBatchResult()

        for signal in pending:
            try:
                item = await self.classify_signal(signal.id)
            except (NotFoundError, ValidationError) as exc:
                item = ClassificationAgentResult(
                    signal_id=signal.id,
                    status="failed",
                    error=str(exc),
                )
            batch_result.add(item)

        logger.info(
            "Classification batch complete",
            extra={
                "classified": batch_result.classified,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def _finalize_signal(
        self,
        signal,
        agent_result: ClassificationAgentResult,
    ) -> ClassificationAgentResult:
        if agent_result.status == "classified" and agent_result.classification is not None:
            classification = agent_result.classification
            resolved = await self._repos.complaints.resolve_category_ids(
                category_code=classification.problem_category,
                domain_code=classification.industry,
                persona_code=classification.customer_type,
            )
            if resolved is None:
                await self._repos.signals.set_processing_status(
                    signal,
                    SignalProcessingStatus.FAILED,
                    skip_reason="taxonomy_resolution_failed",
                )
                agent_result.status = "failed"
                agent_result.error = "taxonomy_resolution_failed"
                return agent_result

            category, domain, persona = resolved
            model = self._last_model(agent_result) or self._settings.classification_model
            complaint = await self._repos.complaints.create(
                ComplaintCreate(
                    signal_id=signal.id,
                    category_id=category.id,
                    domain_id=domain.id,
                    persona_id=persona.id,
                    summary=classification.summary,
                    verbatim_quote=classification.verbatim_quote or "",
                    severity=classification.severity_score,
                    product_mentions=classification.product_mentions,
                    llm_model=model,
                    llm_confidence=classification.confidence,
                    business_function_code=classification.business_function_code,
                    jtbd_code=classification.jtbd_code,
                    consequence_code=classification.consequence_code,
                )
            )
            await self._repos.signals.set_processing_status(
                signal,
                SignalProcessingStatus.CLASSIFIED,
            )
            agent_result.complaint_id = complaint.id
            return agent_result

        if agent_result.status == "skipped":
            await self._repos.signals.set_processing_status(
                signal,
                SignalProcessingStatus.SKIPPED,
                skip_reason=agent_result.skip_reason,
            )
            return agent_result

        await self._repos.signals.set_processing_status(
            signal,
            SignalProcessingStatus.FAILED,
            skip_reason=agent_result.error,
        )
        return agent_result

    async def _persist_eval_logs(
        self,
        signal_id: UUID,
        agent_result: ClassificationAgentResult,
    ) -> None:
        from app.agents.eval_logging import persist_agent_eval_logs

        await persist_agent_eval_logs(
            self._repos,
            budget=self._budget,
            entity_type="signal",
            entity_id=signal_id,
            graph_name=GRAPH_NAME,
            default_model=self._settings.classification_model,
            agent_result=agent_result,
        )

    @staticmethod
    def _last_model(agent_result: ClassificationAgentResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
