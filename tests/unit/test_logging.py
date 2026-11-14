"""Unit tests for production logging, credential redaction, and request correlation."""

from __future__ import annotations

import logging
import pytest
from flask import Flask, g
from app.core.logging import (
    RequestCorrelationFilter,
    SensitiveDataFilter,
    setup_logging,
)


@pytest.mark.unit
class TestLoggingFilters:
    """Test log filters for request correlation and sensitive data redaction."""

    def test_request_correlation_filter_outside_context(self) -> None:
        filter_instance = RequestCorrelationFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=20,
            msg="Hello outside context",
            args=(),
            exc_info=None,
        )
        assert filter_instance.filter(record) is True
        assert record.request_id == "-"

    def test_request_correlation_filter_inside_context(self) -> None:
        app = Flask(__name__)
        filter_instance = RequestCorrelationFilter()

        with app.test_request_context("/test-url"):
            g.request_id = "custom-uuid-12345"
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname=__file__,
                lineno=35,
                msg="Hello inside context",
                args=(),
                exc_info=None,
            )
            assert filter_instance.filter(record) is True
            assert record.request_id == "custom-uuid-12345"

    def test_sensitive_data_filter_masks_credentials(self) -> None:
        filter_instance = SensitiveDataFilter()
        raw_msg = "Connecting to mongodb+srv://app_user:secret_password_999@cluster0.mongodb.net/prod"
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=50,
            msg=raw_msg,
            args=(),
            exc_info=None,
        )
        assert filter_instance.filter(record) is True
        assert "secret_password_999" not in record.msg
        assert record.msg == "Connecting to mongodb+srv://app_user:****@cluster0.mongodb.net/prod"

    def test_sensitive_data_filter_preserves_non_string_msg(self) -> None:
        filter_instance = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=62,
            msg=12345,  # non-string
            args=(),
            exc_info=None,
        )
        assert filter_instance.filter(record) is True
        assert record.msg == 12345


@pytest.mark.unit
class TestRequestCorrelationLifecycle:
    """Test request correlation headers across HTTP request/response cycles."""

    @pytest.fixture
    def app_with_logging(self) -> Flask:
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["LOG_LEVEL"] = "DEBUG"
        setup_logging(app)

        @app.route("/echo-id")
        def echo_endpoint():
            return {"id": g.request_id}

        return app

    def test_auto_generated_request_id_in_response_header(self, app_with_logging: Flask) -> None:
        client = app_with_logging.test_client()
        res = client.get("/echo-id")
        assert res.status_code == 200
        assert "X-Request-ID" in res.headers
        generated_id = res.headers["X-Request-ID"]
        assert len(generated_id) > 0
        assert res.get_json()["id"] == generated_id

    def test_propagates_incoming_correlation_id(self, app_with_logging: Flask) -> None:
        client = app_with_logging.test_client()
        incoming_id = "client-trace-abc-123"
        res = client.get("/echo-id", headers={"X-Request-ID": incoming_id})
        assert res.status_code == 200
        assert res.headers["X-Request-ID"] == incoming_id
        assert res.get_json()["id"] == incoming_id

    def test_setup_logging_idempotent_duplicate_prevention(self, app_with_logging: Flask) -> None:
        # Calling setup_logging again should not duplicate stream handlers
        initial_handlers_count = len(app_with_logging.logger.handlers)
        setup_logging(app_with_logging)
        assert len(app_with_logging.logger.handlers) == initial_handlers_count

