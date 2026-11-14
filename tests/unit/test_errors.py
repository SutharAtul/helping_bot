"""Unit tests for domain exceptions and centralized error handlers."""

from __future__ import annotations

import pytest
from flask import Flask, abort
from pydantic import BaseModel, ValidationError as PydanticValidationError
from app.core.errors import (
    AppError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    _build_error_payload,
    register_error_handlers,
)


class DummyModel(BaseModel):
    name: str
    age: int


@pytest.fixture
def error_test_app() -> Flask:
    """Create an isolated test application with registered error handlers."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_error_handlers(app)

    @app.route("/raise-app-error")
    def trigger_app_error():
        raise AppError("Custom domain error", code="CUSTOM_DOMAIN_ERROR", status_code=418, details={"field": "test"})

    @app.route("/raise-validation-error")
    def trigger_validation_error():
        raise ValidationError("Input validation failed", details={"param": "missing"})

    @app.route("/raise-not-found-error")
    def trigger_not_found_error():
        raise NotFoundError("Resource missing")

    @app.route("/raise-database-error")
    def trigger_database_error():
        raise DatabaseError("Query timed out")

    @app.route("/raise-pydantic-error")
    def trigger_pydantic_error():
        DummyModel(name="test")  # missing required field 'age'

    @app.route("/abort-400")
    def trigger_400():
        abort(400, description="Invalid syntax or payload")

    @app.route("/get-only", methods=["GET"])
    def trigger_405_endpoint():
        return "ok"

    @app.route("/abort-500")
    def trigger_500():
        abort(500)

    @app.route("/unhandled-exception")
    def trigger_unhandled():
        raise RuntimeError("Unexpected failure")

    return app


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

    def test_build_error_payload_format(self) -> None:
        payload = _build_error_payload("CODE_X", "Sample message", {"meta": "val"})
        assert payload["status"] == "error"
        assert payload["error"]["code"] == "CODE_X"
        assert payload["error"]["message"] == "Sample message"
        assert payload["error"]["details"] == {"meta": "val"}


@pytest.mark.unit
class TestCentralizedErrorHandlers:
    """Test standard JSON error responses produced by registered Flask error handlers."""

    def test_handle_custom_app_error(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/raise-app-error")
        assert res.status_code == 418
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "CUSTOM_DOMAIN_ERROR"
        assert data["error"]["message"] == "Custom domain error"
        assert data["error"]["details"] == {"field": "test"}

    def test_handle_domain_validation_error(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/raise-validation-error")
        assert res.status_code == 400
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["details"]["param"] == "missing"

    def test_handle_domain_not_found_error(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/raise-not-found-error")
        assert res.status_code == 404
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "NOT_FOUND"

    def test_handle_domain_database_error(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/raise-database-error")
        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "DATABASE_ERROR"

    def test_handle_pydantic_validation_error(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/raise-pydantic-error")
        assert res.status_code == 400
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "errors" in data["error"]["details"]

    def test_handle_400_bad_request(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/abort-400")
        assert res.status_code == 400
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "BAD_REQUEST"

    def test_handle_404_not_found(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/non-existent-route")
        assert res.status_code == 404
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "NOT_FOUND"

    def test_handle_405_method_not_allowed(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.post("/get-only")
        assert res.status_code == 405
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "METHOD_NOT_ALLOWED"

    def test_handle_500_abort(self, error_test_app: Flask) -> None:
        client = error_test_app.test_client()
        res = client.get("/abort-500")
        assert res.status_code == 500
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"

    def test_handle_500_generic_exception(self, error_test_app: Flask) -> None:
        # Avoid crashing test runner on unhandled 500
        client = error_test_app.test_client()
        res = client.get("/unhandled-exception")
        assert res.status_code == 500
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert data["error"]["message"] == "An unexpected error occurred"
