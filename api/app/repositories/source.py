"""Source repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceType
from app.db.models.source import Source
from app.repositories.base import BaseRepository
from app.schemas.source import SourceCreate, SourceUpdate


class SourceRepository(BaseRepository[Source]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Source)

    async def list_enabled(self) -> list[Source]:
        result = await self.session.execute(
            select(Source).where(Source.enabled.is_(True)).order_by(Source.name)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Source | None:
        result = await self.session.execute(select(Source).where(Source.name == name))
        return result.scalar_one_or_none()

    async def list_by_type(self, source_type: SourceType) -> list[Source]:
        result = await self.session.execute(
            select(Source)
            .where(Source.source_type == source_type.value)
            .order_by(Source.name)
        )
        return list(result.scalars().all())

    async def create(self, data: SourceCreate) -> Source:
        entity = Source(
            name=data.name,
            source_type=data.source_type.value,
            config=data.config,
            enabled=data.enabled,
        )
        return await self.add(entity)

    async def update(self, entity: Source, data: SourceUpdate) -> Source:
        updates = data.model_dump(exclude_unset=True)
        if "source_type" in updates and updates["source_type"] is not None:
            updates["source_type"] = updates["source_type"].value
        for field, value in updates.items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def record_collection_success(self, entity_id: UUID) -> Source | None:
        from datetime import UTC, datetime

        entity = await self.get_by_id(entity_id)
        if entity is None:
            return None
        entity.last_collected_at = datetime.now(UTC)
        entity.last_error = None
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def record_collection_error(self, entity_id: UUID, error: str) -> Source | None:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return None
        entity.last_error = error
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
