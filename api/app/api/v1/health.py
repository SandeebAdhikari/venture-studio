"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app import __version__
from app.api.deps import AppSettings, DbSession, RedisClient
from app.observability.readiness import run_readiness_checks

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = __version__
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReadinessCheck(BaseModel):
    name: str
    status: str
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    checks: list[ReadinessCheck]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns OK if the process is running. Does not check dependencies.",
)
async def liveness() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Verifies PostgreSQL, Redis, worker availability (when required), "
        "scheduler availability (when enabled), and alerting subsystem status."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "One or more dependencies unavailable"
        },
    },
)
async def readiness(
    response: Response,
    db: DbSession,
    redis: RedisClient,
    settings: AppSettings,
) -> ReadinessResponse:
    results = await run_readiness_checks(db=db, redis=redis, settings=settings)
    checks = [
        ReadinessCheck(name=item.name, status=item.status, detail=item.detail)
        for item in results
    ]

    all_ok = all(check.status == "ok" for check in checks)
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ok" if all_ok else "degraded",
        checks=checks,
    )
