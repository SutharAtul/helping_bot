"""Application factory for OTA RAG Bot backend."""

from __future__ import annotations

from flask import Flask, jsonify, Response
from app.config import get_config
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.extensions import mongo
from app.api.v1 import v1_blueprint


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure an instance of the Flask application using factory pattern.

    Args:
        config_name: Environment configuration name ('development', 'testing', 'production').

    Returns:
        Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration
    config_cls = get_config(config_name)
    app.config.from_object(config_cls)

    # Setup structured logging
    setup_logging(app)

    # Initialize extensions
    mongo.init_app(app)

    # Register error handlers
    register_error_handlers(app)

    # Register API blueprints
    app.register_blueprint(v1_blueprint, url_prefix="/api/v1")

    # Root index route
    @app.route("/", methods=["GET"])
    def root() -> tuple[Response, int]:
        return (
            jsonify(
                {
                    "service": app.config.get("APP_NAME", "ota-rag-bot"),
                    "version": app.config.get("VERSION", "0.1.0"),
                    "status": "online",
                    "docs_url": "/api/v1/health",
                }
            ),
            200,
        )

    app.logger.info(
        f"Application initialized successfully in {app.config.get('ENV')} mode"
    )
    return app

