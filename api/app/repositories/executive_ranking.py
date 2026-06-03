"""Executive ranking repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.executive_ranking_entry import ExecutiveRankingEntry
from app.db.models.executive_ranking_run import ExecutiveRankingRun
from app.repositories.base import BaseRepository
from app.schemas.executive_ranking import ExecutiveRankingRunCreate


class ExecutiveRankingRepository(BaseRepository[ExecutiveRankingRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ExecutiveRankingRun)

    async def get_current(self) -> ExecutiveRankingRun | None:
        result = await self.session.execute(
            select(ExecutiveRankingRun).where(ExecutiveRankingRun.is_current.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_entries(self, run_id: UUID) -> ExecutiveRankingRun | None:
        result = await self.session.execute(
            select(ExecutiveRankingRun)
            .options(selectinload(ExecutiveRankingRun.entries))
            .where(ExecutiveRankingRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_current_with_entries(self) -> ExecutiveRankingRun | None:
        result = await self.session.execute(
            select(ExecutiveRankingRun)
            .options(selectinload(ExecutiveRankingRun.entries))
            .where(ExecutiveRankingRun.is_current.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_history(self, *, limit: int = 20, offset: int = 0) -> list[ExecutiveRankingRun]:
        result = await self.session.execute(
            select(ExecutiveRankingRun)
            .order_by(
                ExecutiveRankingRun.version.desc(),
                ExecutiveRankingRun.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_history(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(ExecutiveRankingRun))
        return int(result or 0)

    async def create(self, data: ExecutiveRankingRunCreate) -> ExecutiveRankingRun:
        await self.session.execute(
            update(ExecutiveRankingRun)
            .where(ExecutiveRankingRun.is_current.is_(True))
            .values(is_current=False)
        )

        current_version = await self.session.scalar(select(func.max(ExecutiveRankingRun.version)))
        next_version = int(current_version or 0) + 1

        entity = ExecutiveRankingRun(
            version=next_version,
            status=data.status.value,
            is_current=True,
            founder_profile_id=data.founder_profile_id,
            top_n=data.top_n,
            opportunity_count=data.opportunity_count,
            ranked_opportunity_count=data.ranked_opportunity_count,
            ranking_engine=data.ranking_engine,
            ranking_metadata=data.ranking_metadata,
        )
        entity = await self.add(entity)

        for entry_data in data.entries:
            entry = ExecutiveRankingEntry(
                executive_ranking_run_id=entity.id,
                opportunity_id=entry_data.opportunity_id,
                rank=entry_data.rank,
                final_opportunity_score=entry_data.final_opportunity_score,
                pain_score=entry_data.pain_score,
                market_score=entry_data.market_score,
                revenue_score=entry_data.revenue_score,
                competition_score=entry_data.competition_score,
                growth_score=entry_data.growth_score,
                founder_fit_score=entry_data.founder_fit_score,
                agent_coverage_count=entry_data.agent_coverage_count,
                is_top_opportunity=entry_data.is_top_opportunity,
                source_references=entry_data.source_references,
                ranking_details=entry_data.ranking_details,
            )
            self.session.add(entry)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity
