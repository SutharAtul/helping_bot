"""Integration tests for health, readiness, and liveness endpoints."""

from __future__ import annotations

from unittest.mock import patch
import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health and probe routes."""

    def test_root_endpoint(self, client: FlaskClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "online"
        assert "service" in data
        assert "version" in data

    def test_liveness_endpoint(self, client: FlaskClient) -> None:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "service" in data

    def test_health_check_healthy(self, client: FlaskClient) -> None:
        with patch("app.api.v1.health.mongo.ping", return_value=True):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
            assert data["dependencies"]["mongodb"]["status"] == "healthy"

    def test_health_check_degraded(self, client: FlaskClient) -> None:
        with patch("app.api.v1.health.mongo.ping", return_value=False):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "degraded"
            assert data["dependencies"]["mongodb"]["status"] == "unreachable"

    def test_readiness_probe_ready(self, client: FlaskClient) -> None:
        with patch("app.api.v1.health.mongo.ping", return_value=True):
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ready"

    def test_readiness_probe_not_ready(self, client: FlaskClient) -> None:
        with patch("app.api.v1.health.mongo.ping", return_value=False):
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "not_ready"

    def test_not_found_json_response(self, client: FlaskClient) -> None:
        response = client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == "NOT_FOUND"

