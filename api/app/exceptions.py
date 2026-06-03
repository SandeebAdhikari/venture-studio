"""Application-level exceptions raised by the service layer."""

from uuid import UUID


class AppError(Exception):
    """Base class for domain errors surfaced to the API."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: UUID) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} '{resource_id}' not found")


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ValidationError(AppError):
    """Business validation failure distinct from Pydantic request validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ForbiddenError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
