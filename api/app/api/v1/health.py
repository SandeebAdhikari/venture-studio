"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app import __version__
from app.api.deps import AppSettings, DbSession, RedisClient
from app.logging import get_logger

logger = get_logger(__name__)

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
    description="Verifies PostgreSQL and Redis connectivity.",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "One or more dependencies unavailable"},
    },
)
async def readiness(
    response: Response,
    db: DbSession,
    redis: RedisClient,
    settings: AppSettings,
) -> ReadinessResponse:
    del settings  # reserved for future environment-specific checks
    checks: list[ReadinessCheck] = []

    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        checks.append(ReadinessCheck(name="postgresql", status="ok"))
    except Exception as exc:
        logger.warning("PostgreSQL readiness check failed", exc_info=exc)
        checks.append(ReadinessCheck(name="postgresql", status="error", detail=str(exc)))

    try:
        pong = await redis.ping()
        if pong:
            checks.append(ReadinessCheck(name="redis", status="ok"))
        else:
            checks.append(
                ReadinessCheck(name="redis", status="error", detail="PING did not return True"),
            )
    except Exception as exc:
        logger.warning("Redis readiness check failed", exc_info=exc)
        checks.append(ReadinessCheck(name="redis", status="error", detail=str(exc)))

    all_ok = all(check.status == "ok" for check in checks)
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ok" if all_ok else "degraded",
        checks=checks,
    )
