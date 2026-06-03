"""Complaint repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.category import Category
from app.db.models.complaint import Complaint
from app.repositories.base import BaseRepository
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate


class ComplaintRepository(BaseRepository[Complaint]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Complaint)

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
