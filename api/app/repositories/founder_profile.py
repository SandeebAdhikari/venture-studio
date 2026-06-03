"""Founder profile repository."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.founder_profile import FounderProfile
from app.repositories.base import BaseRepository
from app.schemas.founder_profile import FounderProfileCreate


class FounderProfileRepository(BaseRepository[FounderProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FounderProfile)

    async def get_default(self) -> FounderProfile | None:
        result = await self.session.execute(
            select(FounderProfile).where(
                FounderProfile.is_default.is_(True),
                FounderProfile.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[FounderProfile]:
        result = await self.session.execute(
            select(FounderProfile)
            .where(FounderProfile.is_active.is_(True))
            .order_by(FounderProfile.is_default.desc(), FounderProfile.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(self, data: FounderProfileCreate) -> FounderProfile:
        if data.is_default:
            await self.session.execute(
                update(FounderProfile).where(FounderProfile.is_default.is_(True)).values(is_default=False)
            )

        entity = FounderProfile(
            name=data.name,
            description=data.description,
            skills=data.skills,
            constraints=data.constraints,
            is_default=data.is_default,
            is_active=data.is_active,
            profile_metadata=data.profile_metadata,
        )
        return await self.add(entity)
