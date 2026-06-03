"""Orchestrates pattern detection and opportunity generation."""

from uuid import UUID

from app.agents.opportunity.graph import GRAPH_NAME, OpportunityGeneratorAgent
from app.agents.opportunity.llm_client import OpenAIOpportunityClient, OpportunityLLMClient
from app.agents.opportunity.patterns import TopicPatternDetector
from app.agents.opportunity.schemas import (
    ComplaintEvidence,
    ComplaintPattern,
    GenerationBatchResult,
    OpportunityGenerationResult,
)
from app.config import Settings, get_settings
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.scoring.service import OpportunityScoringService
from app.schemas.opportunity import OpportunityCreate

logger = get_logger(__name__)


class OpportunityGeneratorService:
    """Detects recurring complaint patterns and generates opportunity briefs."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        llm_client: OpportunityLLMClient | None = None,
        pattern_detector: TopicPatternDetector | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._pattern_detector = pattern_detector or TopicPatternDetector()
        self._agent: OpportunityGeneratorAgent | None = None

    def _get_agent(self) -> OpportunityGeneratorAgent:
        if self._agent is None:
            client = self._llm_client or OpenAIOpportunityClient(self._settings)
            self._agent = OpportunityGeneratorAgent(client, self._settings)
        return self._agent

    async def generate(self, *, limit: int | None = None) -> GenerationBatchResult:
        batch_size = limit or self._settings.generation_batch_size
        complaints = await self._repos.complaints.list_unlinked_for_generation(
            window_days=self._settings.cluster_window_days,
            limit=batch_size,
        )
        evidence = [self._to_evidence(complaint) for complaint in complaints]
        patterns = self._pattern_detector.detect(
            evidence,
            min_cluster_size=self._settings.min_cluster_size,
        )

        batch_result = GenerationBatchResult(patterns_found=len(patterns))
        evidence_by_id = {item.id: item for item in evidence}

        for pattern in patterns:
            if pattern.avg_severity < self._settings.min_avg_severity:
                batch_result.add(
                    OpportunityGenerationResult(
                        pattern_topic=pattern.topic,
                        status="skipped",
                        skip_reason="low_avg_severity",
                    )
                )
                continue

            if await self._repos.opportunities.exists_similar_title(pattern.topic):
                batch_result.add(
                    OpportunityGenerationResult(
                        pattern_topic=pattern.topic,
                        status="skipped",
                        skip_reason="duplicate_title",
                    )
                )
                continue

            pattern_evidence = [
                evidence_by_id[complaint_id]
                for complaint_id in pattern.complaint_ids
                if complaint_id in evidence_by_id
            ]
            item = await self.generate_for_pattern(pattern, pattern_evidence)
            batch_result.add(item)

        logger.info(
            "Opportunity generation batch complete",
            extra={
                "patterns_found": batch_result.patterns_found,
                "created": batch_result.created,
                "skipped": batch_result.skipped,
                "failed": batch_result.failed,
            },
        )
        return batch_result

    async def generate_for_pattern(
        self,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
    ) -> OpportunityGenerationResult:
        agent_result = await self._get_agent().run(pattern, evidence)

        if agent_result.status != "created" or agent_result.draft is None:
            return agent_result

        draft = agent_result.draft
        model = self._last_model(agent_result) or self._settings.generation_model
        opportunity = await self._repos.opportunities.create(
            OpportunityCreate(
                title=draft.title,
                problem_statement=draft.problem_statement,
                target_user=draft.target_user,
                frequency_signal=draft.frequency_signal,
                existing_alternatives=draft.existing_alternatives,
                gap=draft.gap,
                confidence_score=draft.confidence_score,
                llm_model=model,
                complaint_ids=draft.complaint_ids,
            )
        )

        scoring_service = OpportunityScoringService(self._repos, self._settings)
        await scoring_service.score_opportunity(opportunity.id, notes=draft.explanation)

        await self._persist_eval_logs(opportunity.id, agent_result)
        agent_result.opportunity_id = opportunity.id
        return agent_result

    async def _persist_eval_logs(
        self,
        opportunity_id: UUID,
        agent_result: OpportunityGenerationResult,
    ) -> None:
        for log in agent_result.eval_logs:
            status = "success" if log.get("error") is None else "error"
            await self._repos.llm_calls.log_agent_call(
                entity_type="opportunity",
                entity_id=opportunity_id,
                graph_name=GRAPH_NAME,
                model=log.get("model", self._settings.generation_model),
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
                    "pattern_topic": agent_result.pattern_topic,
                    "agent_status": agent_result.status,
                    "attempts": agent_result.attempts,
                },
            )

    @staticmethod
    def _to_evidence(complaint) -> ComplaintEvidence:
        return ComplaintEvidence(
            id=complaint.id,
            summary=complaint.summary,
            verbatim_quote=complaint.verbatim_quote,
            severity=complaint.severity,
            domain_code=complaint.domain.code,
            category_code=complaint.category.code,
            persona_code=complaint.persona.code,
            product_mentions=list(complaint.product_mentions or []),
        )

    @staticmethod
    def _last_model(agent_result: OpportunityGenerationResult) -> str | None:
        if not agent_result.eval_logs:
            return None
        return agent_result.eval_logs[-1].get("model")
