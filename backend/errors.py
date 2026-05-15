"""
Standardized application errors for the VMTips backend.

All custom errors inherit from AppError. The global exception handler in
main.py formats every error (AppError or bare HTTPException) into a
consistent JSON structure: {"error": <code>, "detail": <message>}.
"""
from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application error with a machine-readable error_code."""

    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "internal_error",
        detail: str = "An unexpected error occurred",
        headers: dict | None = None,
    ):
        self.error_code = error_code
        # Pass *detail* as the HTTPException detail so that existing code
        # reading exc.detail still works.
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundError(AppError):
    """404 — resource not found."""

    def __init__(self, detail: str = "not_found", error_code: str = "not_found"):
        super().__init__(status_code=404, error_code=error_code, detail=detail)


class UnauthorizedError(AppError):
    """401 — authentication required / failed."""

    def __init__(
        self,
        detail: str = "unauthorized",
        error_code: str = "unauthorized",
        headers: dict | None = None,
    ):
        if headers is None:
            headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(
            status_code=401, error_code=error_code, detail=detail, headers=headers
        )


class ForbiddenError(AppError):
    """403 — authenticated but not authorised."""

    def __init__(self, detail: str = "forbidden", error_code: str = "forbidden"):
        super().__init__(status_code=403, error_code=error_code, detail=detail)


class ValidationError(AppError):
    """400 — client-sent bad data."""

    def __init__(self, detail: str = "validation_error", error_code: str = "validation_error"):
        super().__init__(status_code=400, error_code=error_code, detail=detail)


class ConflictError(AppError):
    """409 — duplicate / conflict."""

    def __init__(self, detail: str = "conflict", error_code: str = "conflict"):
        super().__init__(status_code=409, error_code=error_code, detail=detail)