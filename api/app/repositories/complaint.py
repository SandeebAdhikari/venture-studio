"""Complaint repository."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.associations import opportunity_complaints
from app.db.models.category import Category
from app.db.models.complaint import Complaint
from app.db.models.signal import Signal
from app.repositories.base import BaseRepository
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate
from app.schemas.filters import ComplaintListFilter


class ComplaintRepository(BaseRepository[Complaint]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Complaint)

    def _apply_filters(self, query, filters: ComplaintListFilter):
        if filters.category_id is not None:
            query = query.where(Complaint.category_id == filters.category_id)
        if filters.domain_id is not None:
            query = query.where(Complaint.domain_id == filters.domain_id)
        if filters.persona_id is not None:
            query = query.where(Complaint.persona_id == filters.persona_id)
        if filters.min_severity is not None:
            query = query.where(Complaint.severity >= filters.min_severity)
        if filters.signal_id is not None:
            query = query.where(Complaint.signal_id == filters.signal_id)
        return query

    async def list_filtered(
        self,
        filters: ComplaintListFilter,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Complaint]:
        query = self._apply_filters(select(Complaint), filters)
        result = await self.session.execute(
            query.order_by(Complaint.severity.desc(), Complaint.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_filtered(self, filters: ComplaintListFilter) -> int:
        query = self._apply_filters(select(func.count()).select_from(Complaint), filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def signal_exists(self, signal_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(Signal).where(Signal.id == signal_id)
        )
        return int(result.scalar_one()) > 0

    async def get_by_id_with_relations(self, entity_id: UUID) -> Complaint | None:
        result = await self.session.execute(
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.domain),
                selectinload(Complaint.persona),
                selectinload(Complaint.signal),
            )
            .where(Complaint.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_signal_id(self, signal_id: UUID) -> Complaint | None:
        result = await self.session.execute(
            select(Complaint).where(Complaint.signal_id == signal_id)
        )
        return result.scalar_one_or_none()

    async def list_by_category(self, category_id: UUID, *, limit: int = 50) -> list[Complaint]:
        result = await self.session.execute(
            select(Complaint)
            .where(Complaint.category_id == category_id)
            .order_by(Complaint.severity.desc(), Complaint.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_unembedded(self, *, limit: int = 50) -> list[Complaint]:
        result = await self.session.execute(
            select(Complaint)
            .where(Complaint.embedding.is_(None))
            .order_by(Complaint.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, data: ComplaintCreate) -> Complaint:
        entity = Complaint(
            signal_id=data.signal_id,
            category_id=data.category_id,
            domain_id=data.domain_id,
            persona_id=data.persona_id,
            summary=data.summary,
            verbatim_quote=data.verbatim_quote,
            severity=data.severity,
            product_mentions=data.product_mentions,
            llm_model=data.llm_model,
            llm_confidence=data.llm_confidence,
        )
        return await self.add(entity)

    async def update(self, entity: Complaint, data: ComplaintUpdate) -> Complaint:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def list_by_domain(self, domain_id: UUID, *, limit: int = 50) -> list[Complaint]:
        result = await self.session.execute(
            select(Complaint)
            .where(Complaint.domain_id == domain_id)
            .order_by(Complaint.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def resolve_category_ids(
        self,
        category_code: str,
        domain_code: str,
        persona_code: str,
    ) -> tuple[Category, Category, Category] | None:
        """Resolve taxonomy codes to category rows."""
        category = await self.session.scalar(
            select(Category).where(
                Category.code == category_code,
                Category.kind == "complaint_category",
            )
        )
        domain = await self.session.scalar(
            select(Category).where(Category.code == domain_code, Category.kind == "domain")
        )
        persona = await self.session.scalar(
            select(Category).where(Category.code == persona_code, Category.kind == "persona")
        )
        if category is None or domain is None or persona is None:
            return None
        return category, domain, persona

    async def list_unlinked_for_generation(
        self,
        *,
        window_days: int = 30,
        limit: int = 500,
    ) -> list[Complaint]:
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        linked_ids = select(opportunity_complaints.c.complaint_id)
        result = await self.session.execute(
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.domain),
                selectinload(Complaint.persona),
            )
            .where(
                Complaint.created_at >= cutoff,
                Complaint.id.not_in(linked_ids),
            )
            .order_by(Complaint.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
