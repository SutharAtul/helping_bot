"""Global error handlers and custom application exceptions."""

from __future__ import annotations

import logging
from typing import Any, Optional
from flask import Flask, jsonify, Response
from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application exception for domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    """Exception raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class NotFoundError(AppError):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class DatabaseError(AppError):
    """Exception raised for database-related operational errors."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=503,
            details=details,
        )


def _build_error_payload(
    code: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Helper to build standardized JSON error envelope."""
    return {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def register_error_handlers(app: Flask) -> None:
    """Register custom error handlers for standard HTTP codes and domain exceptions."""

    @app.errorhandler(AppError)
    def handle_app_error(err: AppError) -> tuple[Response, int]:
        logger.warning(f"AppError [{err.code}]: {err.message} (details: {err.details})")
        payload = _build_error_payload(err.code, err.message, err.details)
        return jsonify(payload), err.status_code

    @app.errorhandler(PydanticValidationError)
    def handle_pydantic_validation_error(err: PydanticValidationError) -> tuple[Response, int]:
        logger.warning(f"Pydantic validation error: {err.errors()}")
        payload = _build_error_payload(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": err.errors()},
        )
        return jsonify(payload), 400

    @app.errorhandler(400)
    def handle_bad_request(err: HTTPException) -> tuple[Response, int]:
        payload = _build_error_payload("BAD_REQUEST", err.description or "Bad request")
        return jsonify(payload), 400

    @app.errorhandler(404)
    def handle_not_found(err: HTTPException) -> tuple[Response, int]:
        payload = _build_error_payload("NOT_FOUND", "The requested URL was not found on the server")
        return jsonify(payload), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(err: HTTPException) -> tuple[Response, int]:
        payload = _build_error_payload("METHOD_NOT_ALLOWED", "The method is not allowed for the requested URL")
        return jsonify(payload), 405

    @app.errorhandler(500)
    def handle_internal_server_error(err: Exception) -> tuple[Response, int]:
        logger.exception(f"Unhandled 500 error: {err}")
        payload = _build_error_payload("INTERNAL_SERVER_ERROR", "An unexpected error occurred")
        return jsonify(payload), 500

    @app.errorhandler(Exception)
    def handle_generic_exception(err: Exception) -> tuple[Response, int]:
        logger.exception(f"Unhandled exception: {err}")
        payload = _build_error_payload("INTERNAL_SERVER_ERROR", "An unexpected error occurred")
        return jsonify(payload), 500

