"""Health check, liveness, and readiness endpoints for API v1."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, Response
from app.extensions import mongo
from app.schemas.health import (
    DependencyStatus,
    HealthCheckResponse,
    LivenessResponse,
    ReadinessResponse,
)

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check() -> tuple[Response, int]:
    """Comprehensive health check including external dependency inspection."""
    mongo_healthy = mongo.ping()
    mongo_status = DependencyStatus(
        status="healthy" if mongo_healthy else "unreachable",
        message="Connected to cluster" if mongo_healthy else "Cannot ping MongoDB cluster",
    )

    overall_status = "healthy" if mongo_healthy else "degraded"

    response_data = HealthCheckResponse(
        status=overall_status,
        service=current_app.config.get("APP_NAME", "ota-rag-bot"),
        version=current_app.config.get("VERSION", "0.1.0"),
        environment=current_app.config.get("APP_ENV") or current_app.config.get("ENV", "unknown"),
        dependencies={"mongodb": mongo_status},
    )

    status_code = 200 if overall_status in ("healthy", "degraded") else 503
    return jsonify(response_data.model_dump(mode="json")), status_code


@health_bp.route("/health/live", methods=["GET"])
def liveness() -> tuple[Response, int]:
    """Kubernetes / orchestration liveness probe."""
    response_data = LivenessResponse(
        status="alive",
        service=current_app.config.get("APP_NAME", "ota-rag-bot"),
    )
    return jsonify(response_data.model_dump(mode="json")), 200


@health_bp.route("/health/ready", methods=["GET"])
def readiness() -> tuple[Response, int]:
    """Kubernetes / orchestration readiness probe."""
    mongo_healthy = mongo.ping()
    mongo_status = DependencyStatus(
        status="healthy" if mongo_healthy else "unreachable",
        message="Connected to cluster" if mongo_healthy else "Cannot ping MongoDB cluster",
    )

    is_ready = mongo_healthy
    response_data = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        service=current_app.config.get("APP_NAME", "ota-rag-bot"),
        dependencies={"mongodb": mongo_status},
    )

    status_code = 200 if is_ready else 503
    return jsonify(response_data.model_dump(mode="json")), status_code
