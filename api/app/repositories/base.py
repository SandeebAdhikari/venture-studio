"""Generic async repository base class."""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Provides common CRUD operations for SQLAlchemy models."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def _base_select(self) -> Select[tuple[ModelT]]:
        return select(self.model)

    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        result = await self.session.execute(
            self._base_select().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModelT]:
        result = await self.session.execute(
            self._base_select()
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return int(result.scalar_one())

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def refresh(self, entity: ModelT) -> ModelT:
        await self.session.refresh(entity)
        return entity
