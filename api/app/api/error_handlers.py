"""Global exception handlers for the FastAPI application."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.exceptions import ValidationError as ServiceValidationError
from app.logging import get_logger
from app.observability.errors import capture_exception

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": exc.message,
                "resource": exc.resource,
                "resource_id": str(exc.resource_id),
            },
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "conflict", "message": exc.message},
        )

    @app.exception_handler(ServiceValidationError)
    async def service_validation_handler(
        _request: Request,
        exc: ServiceValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "validation_error", "message": exc.message},
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(_request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "forbidden", "message": exc.message},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        logger.error("Unhandled application error", extra={"error_message": exc.message})
        capture_exception(exc, context={"error_type": "app_error"})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "request_validation_error", "details": exc.errors()},
        )

    @app.exception_handler(ValidationError)
    async def response_validation_handler(
        _request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        logger.error("Response validation failed", exc_info=exc)
        capture_exception(exc, context={"error_type": "response_validation_error"})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "response_validation_error",
                "message": "Internal response format error",
            },
        )
