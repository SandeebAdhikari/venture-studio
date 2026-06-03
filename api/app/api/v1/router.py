"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import health

router = APIRouter()

# Health routes are also mounted at root level in main.py for k8s/docker probes.
router.include_router(health.router)

# Future routers (opportunities, signals, sources, pipeline) attach here.
