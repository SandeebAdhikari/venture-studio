"""ORM model registry.

Import all model modules here so Alembic autogenerate can discover metadata.
Business models will be added in subsequent milestones.
"""

from app.db.base import Base

__all__ = ["Base"]
