"""Service layer for opportunity scoring and score history."""

from uuid import UUID

from app.config import Settings, get_settings
from app.exceptions import NotFoundError, ValidationError
from app.logging import get_logger
from app.repositories import RepositoryContainer
from app.schemas.filters import OpportunityListFilter
from app.schemas.opportunity_score import OpportunityScoreCreate
from app.scoring.engine import SCORING_MODEL, OpportunityScoringEngine
from app.scoring.schemas import OpportunityScoreRecord, ScoringInput, ScoringResult

logger = get_logger(__name__)


class OpportunityScoringService:
    """Computes and persists 0–100 opportunity scores with full history."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
        engine: OpportunityScoringEngine | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._engine = engine or OpportunityScoringEngine(
            volume_target=self._settings.scoring_volume_target,
        )

    async def score_opportunity(
        self,
        opportunity_id: UUID,
        *,
        notes: str | None = None,
    ) -> OpportunityScoreRecord:
        opportunity = await self._repos.opportunities.get_by_id_with_relations(opportunity_id)
        if opportunity is None:
            raise NotFoundError("opportunity", opportunity_id)

        if not opportunity.complaints:
            raise ValidationError(
                f"Opportunity '{opportunity_id}' has no linked complaints to score"
            )

        scoring_input = self._build_input(opportunity)
        result = self._engine.score(scoring_input)
        persisted = await self._persist_score(opportunity_id, result, notes=notes)

        logger.info(
            "Opportunity scored",
            extra={
                "opportunity_id": str(opportunity_id),
                "score": result.score,
                "complaint_count": scoring_input.complaint_count,
            },
        )
        return persisted

    async def rescore_opportunity(
        self,
        opportunity_id: UUID,
        *,
        notes: str | None = None,
    ) -> OpportunityScoreRecord:
        """Recompute score and append a new history row."""
        return await self.score_opportunity(opportunity_id, notes=notes)

    async def score_all(self, *, limit: int = 100) -> list[OpportunityScoreRecord]:
        opportunities = await self._repos.opportunities.list_filtered(
            OpportunityListFilter(),
            limit=limit,
            offset=0,
        )
        records: list[OpportunityScoreRecord] = []
        for opportunity in opportunities:
            loaded = await self._repos.opportunities.get_by_id_with_relations(opportunity.id)
            if loaded is None or not loaded.complaints:
                continue
            try:
                records.append(await self.score_opportunity(loaded.id))
            except ValidationError:
                continue
        return records

    async def get_score_history(self, opportunity_id: UUID) -> list[OpportunityScoreRecord]:
        if await self._repos.opportunities.get_by_id(opportunity_id) is None:
            raise NotFoundError("opportunity", opportunity_id)

        rows = await self._repos.opportunity_scores.list_for_opportunity(opportunity_id)
        return [self._to_record(row) for row in rows]

    async def get_current_score(self, opportunity_id: UUID) -> OpportunityScoreRecord | None:
        row = await self._repos.opportunity_scores.get_current_for_opportunity(opportunity_id)
        if row is None:
            return None
        return self._to_record(row)

    async def _persist_score(
        self,
        opportunity_id: UUID,
        result: ScoringResult,
        *,
        notes: str | None,
    ) -> OpportunityScoreRecord:
        explanation = notes or result.explanation
        entity = await self._repos.opportunity_scores.create(
            OpportunityScoreCreate(
                opportunity_id=opportunity_id,
                score=result.score,
                overall_score=result.overall_score,
                confidence_score=result.confidence_score,
                frequency_score=result.volume_score,
                severity_score=result.severity_score,
                evidence_score=result.market_indicator_score,
                volume_score=result.volume_score,
                market_indicator_score=result.market_indicator_score,
                implementation_ease_score=result.implementation_ease_score,
                founder_fit_score=result.founder_fit_score,
                scoring_model=SCORING_MODEL,
                scoring_notes=explanation,
            )
        )
        return self._to_record(entity)

    def _build_input(self, opportunity) -> ScoringInput:
        complaints = opportunity.complaints
        severities = [complaint.severity for complaint in complaints]
        avg_severity = sum(severities) / len(severities)

        product_mentions = {
            product
            for complaint in complaints
            for product in complaint.product_mentions
            if product.strip()
        }

        domain_code = complaints[0].domain.code if complaints[0].domain else "other"
        category_code = complaints[0].category.code if complaints[0].category else "other"
        persona_counts: dict[str, int] = {}
        for complaint in complaints:
            if complaint.persona:
                persona_counts[complaint.persona.code] = (
                    persona_counts.get(complaint.persona.code, 0) + 1
                )
        dominant_persona = (
            max(persona_counts, key=persona_counts.get) if persona_counts else "other"
        )

        return ScoringInput(
            opportunity_id=opportunity.id,
            confidence_score=opportunity.confidence_score,
            complaint_count=len(complaints),
            avg_severity=avg_severity,
            max_severity=max(severities),
            domain_code=domain_code,
            category_code=category_code,
            dominant_persona_code=dominant_persona,
            unique_product_count=len(product_mentions),
            has_documented_alternatives=bool(opportunity.existing_alternatives.strip()),
            gap_text=opportunity.gap,
        )

    @staticmethod
    def _to_record(entity) -> OpportunityScoreRecord:
        from app.scoring.schemas import DimensionScores

        return OpportunityScoreRecord(
            id=entity.id,
            opportunity_id=entity.opportunity_id,
            score=entity.score,
            is_current=entity.is_current,
            scoring_model=entity.scoring_model,
            explanation=entity.scoring_notes,
            dimensions=DimensionScores(
                volume=int(round(entity.volume_score * 100)),
                severity=int(round(entity.severity_score * 100)),
                market_indicators=int(round(entity.market_indicator_score * 100)),
                implementation_ease=int(round(entity.implementation_ease_score * 100)),
                founder_fit=int(round(entity.founder_fit_score * 100)),
            ),
        )
