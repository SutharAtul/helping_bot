"""API v1 root module with blueprint aggregation."""

from __future__ import annotations

from flask import Blueprint
from app.api.v1.health import health_bp

v1_blueprint = Blueprint("api_v1", __name__)
v1_blueprint.register_blueprint(health_bp)

