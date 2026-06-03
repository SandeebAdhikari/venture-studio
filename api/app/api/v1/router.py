"""API v1 router aggregation."""

from fastapi import APIRouter, Depends

from app.api.deps import verify_api_key
from app.api.v1 import categories, complaints, competitor_intelligence, health, market_research, opportunities, reports, sources

router = APIRouter()

# Public health probes (also mounted at app root).
router.include_router(health.router)

# Authenticated resource APIs.
protected_router = APIRouter(dependencies=[Depends(verify_api_key)])
protected_router.include_router(sources.router)
protected_router.include_router(categories.router)
protected_router.include_router(complaints.router)
protected_router.include_router(opportunities.router)
protected_router.include_router(reports.router)
protected_router.include_router(market_research.router)
protected_router.include_router(competitor_intelligence.router)

router.include_router(protected_router)
