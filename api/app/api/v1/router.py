"""API v1 router aggregation."""

from fastapi import APIRouter, Depends

from app.api.deps import verify_api_key
from app.api.v1 import categories, complaints, competitor_intelligence, customer_research, executive_ranking, executive_reports, go_to_market, growth_strategy, health, human_proxy, market_research, opportunities, pipeline, product_strategy, reports, revenue_validation, sources

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
protected_router.include_router(customer_research.router)
protected_router.include_router(revenue_validation.router)
protected_router.include_router(product_strategy.router)
protected_router.include_router(go_to_market.router)
protected_router.include_router(growth_strategy.router)
protected_router.include_router(human_proxy.router)
protected_router.include_router(executive_ranking.router)
protected_router.include_router(executive_reports.router)
protected_router.include_router(pipeline.router)

router.include_router(protected_router)
