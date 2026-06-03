"""Opportunity score repository."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.opportunity_score import OpportunityScore
from app.repositories.base import BaseRepository
from app.schemas.opportunity_score import OpportunityScoreCreate, OpportunityScoreUpdate


class OpportunityScoreRepository(BaseRepository[OpportunityScore]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OpportunityScore)

    async def get_current_for_opportunity(
        self,
        opportunity_id: UUID,
    ) -> OpportunityScore | None:
        result = await self.session.execute(
            select(OpportunityScore).where(
                OpportunityScore.opportunity_id == opportunity_id,
                OpportunityScore.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[OpportunityScore]:
        result = await self.session.execute(
            select(OpportunityScore)
            .where(OpportunityScore.opportunity_id == opportunity_id)
            .order_by(OpportunityScore.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, data: OpportunityScoreCreate) -> OpportunityScore:
        await self.session.execute(
            update(OpportunityScore)
            .where(
                OpportunityScore.opportunity_id == data.opportunity_id,
                OpportunityScore.is_current.is_(True),
            )
            .values(is_current=False)
        )

        entity = OpportunityScore(
            opportunity_id=data.opportunity_id,
            score=data.score,
            overall_score=data.overall_score,
            confidence_score=data.confidence_score,
            frequency_score=data.frequency_score,
            severity_score=data.severity_score,
            evidence_score=data.evidence_score,
            volume_score=data.volume_score,
            market_indicator_score=data.market_indicator_score,
            implementation_ease_score=data.implementation_ease_score,
            founder_fit_score=data.founder_fit_score,
            scoring_model=data.scoring_model,
            scoring_notes=data.scoring_notes,
            is_current=True,
        )
        return await self.add(entity)

    async def update(
        self,
        entity: OpportunityScore,
        data: OpportunityScoreUpdate,
    ) -> OpportunityScore:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def list_top_ranked(self, *, limit: int = 20) -> list[OpportunityScore]:
        result = await self.session.execute(
            select(OpportunityScore)
            .where(OpportunityScore.is_current.is_(True))
            .order_by(OpportunityScore.overall_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
