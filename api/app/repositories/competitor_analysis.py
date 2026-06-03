"""Competitor analysis repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import CompetitorAnalysisStatus
from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.competitor_profile import CompetitorProfile
from app.db.models.opportunity import Opportunity
from app.repositories.base import BaseRepository
from app.schemas.competitor_analysis import CompetitorAnalysisCreate
from app.schemas.filters import CompetitorAnalysisListFilter


class CompetitorAnalysisRepository(BaseRepository[CompetitorAnalysis]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorAnalysis)

    def _apply_filters(self, query, filters: CompetitorAnalysisListFilter):
        if filters.opportunity_id is not None:
            query = query.where(CompetitorAnalysis.opportunity_id == filters.opportunity_id)
        if filters.status is not None:
            query = query.where(CompetitorAnalysis.status == filters.status.value)
        if filters.is_current is not None:
            query = query.where(CompetitorAnalysis.is_current.is_(filters.is_current))
        return query

    async def get_current_for_opportunity(
        self,
        opportunity_id: UUID,
    ) -> CompetitorAnalysis | None:
        result = await self.session.execute(
            select(CompetitorAnalysis).where(
                CompetitorAnalysis.opportunity_id == opportunity_id,
                CompetitorAnalysis.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_profiles(self, entity_id: UUID) -> CompetitorAnalysis | None:
        result = await self.session.execute(
            select(CompetitorAnalysis)
            .options(selectinload(CompetitorAnalysis.profiles))
            .where(CompetitorAnalysis.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_opportunity(self, opportunity_id: UUID) -> list[CompetitorAnalysis]:
        result = await self.session.execute(
            select(CompetitorAnalysis)
            .where(CompetitorAnalysis.opportunity_id == opportunity_id)
            .order_by(CompetitorAnalysis.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        filters: CompetitorAnalysisListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CompetitorAnalysis]:
        query = self._apply_filters(select(CompetitorAnalysis), filters)
        result = await self.session.execute(
            query.order_by(CompetitorAnalysis.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: CompetitorAnalysisListFilter) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(CompetitorAnalysis),
            filters,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_opportunity_ids_without_analysis(self, *, limit: int) -> list[UUID]:
        analyzed_subq = select(CompetitorAnalysis.opportunity_id).where(
            CompetitorAnalysis.is_current.is_(True),
            CompetitorAnalysis.status == CompetitorAnalysisStatus.COMPLETED.value,
        )
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.id.not_in(analyzed_subq))
            .order_by(Opportunity.created_at.asc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]

    async def list_opportunity_ids(self, *, limit: int) -> list[UUID]:
        result = await self.session.execute(
            select(Opportunity.id).order_by(Opportunity.created_at.asc()).limit(limit)
        )
        return [row[0] for row in result.all()]

    async def create(self, data: CompetitorAnalysisCreate) -> CompetitorAnalysis:
        await self.session.execute(
            update(CompetitorAnalysis)
            .where(
                CompetitorAnalysis.opportunity_id == data.opportunity_id,
                CompetitorAnalysis.is_current.is_(True),
            )
            .values(is_current=False)
        )

        current_version = await self.session.scalar(
            select(func.max(CompetitorAnalysis.version)).where(
                CompetitorAnalysis.opportunity_id == data.opportunity_id
            )
        )
        next_version = int(current_version or 0) + 1

        entity = CompetitorAnalysis(
            opportunity_id=data.opportunity_id,
            version=next_version,
            status=data.status.value,
            is_current=True,
            competitive_gaps=data.competitive_gaps,
            executive_summary=data.executive_summary,
            evaluation_metrics=data.evaluation_metrics,
            llm_model=data.llm_model,
            analysis_metadata=data.analysis_metadata,
        )
        entity = await self.add(entity)

        for profile_data in data.profiles:
            profile = CompetitorProfile(
                competitor_analysis_id=entity.id,
                name=profile_data.name,
                positioning=profile_data.positioning,
                pricing_model=profile_data.pricing_model,
                strengths=profile_data.strengths,
                weaknesses=profile_data.weaknesses,
                customer_complaints=profile_data.customer_complaints,
                review_sentiment=profile_data.review_sentiment,
                sentiment_score=profile_data.sentiment_score,
                source_basis=profile_data.source_basis,
                profile_metadata=profile_data.profile_metadata,
            )
            self.session.add(profile)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity
