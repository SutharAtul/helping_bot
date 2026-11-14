"""Unit tests for domain exceptions and error handlers."""

from __future__ import annotations

import pytest
from app.core.errors import AppError, NotFoundError, ValidationError, DatabaseError


@pytest.mark.unit
class TestErrors:
    """Test custom exception hierarchy and payloads."""

    def test_app_error_defaults(self) -> None:
        err = AppError("Something went wrong")
        assert err.message == "Something went wrong"
        assert err.code == "INTERNAL_ERROR"
        assert err.status_code == 500
        assert err.details == {}

    def test_validation_error(self) -> None:
        err = ValidationError("Field missing", details={"field": "query"})
        assert err.message == "Field missing"
        assert err.code == "VALIDATION_ERROR"
        assert err.status_code == 400
        assert err.details == {"field": "query"}

    def test_not_found_error(self) -> None:
        err = NotFoundError("Document not found")
        assert err.code == "NOT_FOUND"
        assert err.status_code == 404

    def test_database_error(self) -> None:
        err = DatabaseError("Connection refused")
        assert err.code == "DATABASE_ERROR"
        assert err.status_code == 503

