"""Category repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CategoryKind
from app.db.models.category import Category
from app.repositories.base import BaseRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.filters import CategoryListFilter


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Category)

    def _apply_filters(self, query, filters: CategoryListFilter):
        if filters.kind is not None:
            query = query.where(Category.kind == filters.kind.value)
        if filters.code is not None:
            query = query.where(Category.code == filters.code)
        return query

    async def list_filtered(
        self,
        filters: CategoryListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Category]:
        query = self._apply_filters(select(Category), filters)
        result = await self.session.execute(
            query.order_by(Category.kind, Category.label).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: CategoryListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(Category), filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def get_by_code_and_kind(self, code: str, kind: CategoryKind) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.code == code, Category.kind == kind.value)
        )
        return result.scalar_one_or_none()

    async def list_by_kind(self, kind: CategoryKind) -> list[Category]:
        result = await self.session.execute(
            select(Category).where(Category.kind == kind.value).order_by(Category.label)
        )
        return list(result.scalars().all())

    async def create(self, data: CategoryCreate) -> Category:
        entity = Category(
            code=data.code,
            label=data.label,
            description=data.description,
            kind=data.kind.value,
        )
        return await self.add(entity)

    async def update(self, entity: Category, data: CategoryUpdate) -> Category:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
