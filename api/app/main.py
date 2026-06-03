"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.error_handlers import register_exception_handlers
from app.api.v1 import health
from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.core.lifespan import lifespan

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    description=(
        "AI Venture Studio API for discovering, classifying, and ranking software "
        "business opportunities from public signals."
    ),
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "local" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Liveness/readiness at root (no auth, no /api/v1 prefix) for load balancers
app.include_router(health.router)

# Versioned API surface
app.include_router(v1_router, prefix=settings.api_v1_prefix)
