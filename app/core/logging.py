"""Production-grade logging configuration for OTA RAG Bot."""

from __future__ import annotations

import logging
import sys
from flask import Flask


def setup_logging(app: Flask) -> None:
    """Configure structured console logging for the application."""
    log_level_name: str = app.config.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Standard production log format
    log_format = (
        "[%(asctime)s] [%(process)d] [%(levelname)s] "
        "[%(name)s:%(lineno)d] %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S %z"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # Configure console stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)

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

    app.logger.debug(f"Logging initialized at level: {log_level_name}")

