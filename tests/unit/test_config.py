"""Unit tests for configuration loaders and environments."""

from __future__ import annotations

import pytest
from app.config import (
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config,
)


@pytest.mark.unit
class TestConfig:
    """Test configuration selection and environment properties."""

    def test_development_config(self) -> None:
        cfg = get_config("development")
        assert issubclass(cfg, DevelopmentConfig)
        assert cfg.DEBUG is True
        assert cfg.TESTING is False
        assert cfg.ENV == "development"

    def test_testing_config(self) -> None:
        cfg = get_config("testing")
        assert issubclass(cfg, TestingConfig)
        assert cfg.TESTING is True
        assert cfg.DEBUG is True
        assert cfg.ENV == "testing"

    def test_production_config(self) -> None:
        cfg = get_config("production")
        assert issubclass(cfg, ProductionConfig)
        assert cfg.DEBUG is False
        assert cfg.TESTING is False
        assert cfg.ENV == "production"

    def test_default_fallback_config(self) -> None:
        # Unknown env should fall back to DevelopmentConfig
        cfg = get_config("nonexistent_env")
        assert issubclass(cfg, DevelopmentConfig)

