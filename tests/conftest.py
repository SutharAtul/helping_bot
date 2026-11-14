"""Pytest fixtures for unit and integration testing."""

from __future__ import annotations

import os
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner

# Enforce testing environment before application initialization
os.environ["APP_ENV"] = "testing"

from app import create_app
from app.extensions import mongo


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create and configure a testing Flask application instance without live dependencies."""
    app_instance = create_app(config_name="testing")

    # Establish an application context before running tests
    with app_instance.app_context():
        yield app_instance

    # Cleanup connection pools after test session
    mongo.close()


@pytest.fixture(scope="function")
def client(app: Flask) -> FlaskClient:
    """Provide a test client for simulating HTTP requests."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app: Flask) -> FlaskCliRunner:
    """Provide a CLI test runner for Flask commands."""
    return app.test_cli_runner()
