"""Production-grade logging configuration for OTA RAG Bot with redaction and request correlation."""

from __future__ import annotations

import logging
import sys
import uuid
from flask import Flask, g, has_request_context, request
from app.config import mask_connection_uri


class RequestCorrelationFilter(logging.Filter):
    """Filter that injects the active request ID into the log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.request_id = getattr(g, "request_id", "-")
        else:
            record.request_id = "-"
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter that automatically masks credentials and sensitive connection URIs in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_connection_uri(record.msg)
        return True


def setup_logging(app: Flask) -> None:
    """Configure structured console logging with request correlation and sensitive data redaction."""
    log_level_name: str = app.config.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Standard production log format including correlation ID
    log_format = (
        "[%(asctime)s] [%(process)d] [%(request_id)s] [%(levelname)s] "
        "[%(name)s:%(lineno)d] %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S %z"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    correlation_filter = RequestCorrelationFilter()
    redaction_filter = SensitiveDataFilter()

    # Configure console stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)
    stream_handler.addFilter(correlation_filter)
    stream_handler.addFilter(redaction_filter)

    # Attach to root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(stream_handler)

    # Align Flask app logger
    app.logger.setLevel(log_level)
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(stream_handler)

    # Register request correlation lifecycle hooks
    @app.before_request
    def set_request_correlation_id() -> None:
        req_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
        g.request_id = req_id if req_id else str(uuid.uuid4())

    @app.after_request
    def attach_correlation_id_header(response):
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        return response

    app.logger.debug(f"Logging initialized at level: {log_level_name}")
