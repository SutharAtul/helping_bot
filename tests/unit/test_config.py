"""Unit tests for centralized environment-based configuration."""

from __future__ import annotations

import os
from unittest.mock import patch
import pytest
from app import create_app
from app.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config,
    load_environment,
    mask_connection_uri,
    mask_secret,
)


@pytest.mark.unit
class TestConfigurationBasics:
    """Test configuration hierarchy, defaults, and environment parsing."""

    def test_development_config_defaults(self) -> None:
        cfg = get_config("development")
        assert issubclass(cfg, DevelopmentConfig)
        assert cfg.APP_ENV == "development"
        assert cfg.DEBUG is True
        assert cfg.TESTING is False
        assert cfg.PORT == 5000
        assert cfg.MAX_CONTENT_LENGTH == 16 * 1024 * 1024

    def test_testing_config_defaults(self) -> None:
        cfg = get_config("testing")
        assert issubclass(cfg, TestingConfig)
        assert cfg.APP_ENV == "testing"
        assert cfg.TESTING is True
        assert cfg.DEBUG is True
        assert cfg.MONGODB_DATABASE == "ota_rag_test_db"
        assert cfg.MONGODB_URI == "mongodb://localhost:27017"

    def test_testing_config_custom_test_env_vars(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MONGODB_TEST_URI": "mongodb://test-cluster:27017",
                "MONGODB_TEST_DATABASE": "custom_test_suite_db",
                "SECRET_KEY": "test-custom-secret",
            },
        ):
            cfg = get_config("testing")
            assert cfg.MONGODB_URI == "mongodb://test-cluster:27017"
            assert cfg.MONGODB_DATABASE == "custom_test_suite_db"
            assert cfg.SECRET_KEY == "test-custom-secret"

    def test_custom_port_and_max_content_length(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PORT": "8080",
                "MAX_CONTENT_LENGTH": "8388608",
                "LOG_LEVEL": "WARNING",
            },
        ):
            cfg = get_config("development")
            assert cfg.PORT == 8080
            assert cfg.MAX_CONTENT_LENGTH == 8388608
            assert cfg.LOG_LEVEL == "WARNING"

    def test_invalid_port_and_length_fallbacks(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PORT": "not-a-port",
                "MAX_CONTENT_LENGTH": "not-a-length",
            },
        ):
            cfg = get_config("development")
            assert cfg.PORT == 5000
            assert cfg.MAX_CONTENT_LENGTH == 16 * 1024 * 1024

    def test_timeout_and_pool_size_parsing(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MONGODB_CONNECT_TIMEOUT_MS": "3500",
                "MONGODB_SERVER_SELECTION_TIMEOUT_MS": "4500",
                "MONGODB_SOCKET_TIMEOUT_MS": "12000",
                "MONGODB_MAX_POOL_SIZE": "80",
                "MONGODB_MIN_POOL_SIZE": "10",
            },
        ):
            cfg = get_config("development")
            assert cfg.MONGODB_CONNECT_TIMEOUT_MS == 3500
            assert cfg.MONGODB_SERVER_SELECTION_TIMEOUT_MS == 4500
            assert cfg.MONGODB_SOCKET_TIMEOUT_MS == 12000
            assert cfg.MONGODB_MAX_POOL_SIZE == 80
            assert cfg.MONGODB_MIN_POOL_SIZE == 10

    def test_timeout_and_pool_size_invalid_fallbacks(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MONGODB_CONNECT_TIMEOUT_MS": "invalid",
                "MONGODB_SERVER_SELECTION_TIMEOUT_MS": "invalid",
                "MONGODB_SOCKET_TIMEOUT_MS": "invalid",
                "MONGODB_MAX_POOL_SIZE": "invalid",
                "MONGODB_MIN_POOL_SIZE": "invalid",
            },
        ):
            # Should not raise exception, falls back to existing values
            cfg = get_config("development")
            assert isinstance(cfg.MONGODB_CONNECT_TIMEOUT_MS, int)
            assert isinstance(cfg.MONGODB_MAX_POOL_SIZE, int)

    def test_get_config_fallback_to_development(self) -> None:
        cfg = get_config("unknown_environment")
        assert issubclass(cfg, DevelopmentConfig)
        assert cfg.APP_ENV == "development"

    def test_get_config_from_app_env_variable(self) -> None:
        with patch.dict(os.environ, {"APP_ENV": "testing"}):
            cfg = get_config()
            assert issubclass(cfg, TestingConfig)


@pytest.mark.unit
class TestProductionValidation:
    """Test startup validation rules for production environments."""

    @pytest.fixture(autouse=True)
    def clean_env(self) -> None:
        """Reset ProductionConfig values before each validation test."""
        ProductionConfig.SECRET_KEY = "dev-insecure-secret-key-change-in-production"
        ProductionConfig.MONGODB_URI = "mongodb://localhost:27017"
        ProductionConfig.MONGODB_DATABASE = "ota_rag_db"
        ProductionConfig.PORT = 5000
        ProductionConfig.MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    def test_valid_production_config(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "a-very-strong-and-secure-random-secret-key-12345",
                "MONGODB_URI": "mongodb+srv://user:pass@cluster.mongodb.net",
                "MONGODB_DATABASE": "ota_production_db",
                "PORT": "5000",
                "MAX_CONTENT_LENGTH": "16777216",
            },
        ):
            cfg = get_config("production")
            # Should not raise exception
            cfg.validate()

    def test_missing_secret_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "",
                "MONGODB_URI": "mongodb://dbserver:27017",
                "MONGODB_DATABASE": "prod_db",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="SECRET_KEY must be set in production"):
                cfg.validate()

    def test_insecure_placeholder_secret_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "replace-with-a-secure-random-secret-key",
                "MONGODB_URI": "mongodb://dbserver:27017",
                "MONGODB_DATABASE": "prod_db",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="insecure default/placeholder value"):
                cfg.validate()

    def test_short_secret_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "short-key",
                "MONGODB_URI": "mongodb://dbserver:27017",
                "MONGODB_DATABASE": "prod_db",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="SECRET_KEY is too short"):
                cfg.validate()

    def test_missing_mongodb_uri(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "valid-and-sufficiently-long-secret-key-prod",
                "MONGODB_URI": "",
                "MONGO_URI": "",
                "MONGODB_DATABASE": "prod_db",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="MONGODB_URI must be set in production"):
                cfg.validate()

    def test_invalid_mongodb_uri_protocol(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "valid-and-sufficiently-long-secret-key-prod",
                "MONGODB_URI": "http://invalid-mongo-host:27017",
                "MONGODB_DATABASE": "prod_db",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="valid connection URI starting with 'mongodb://'"):
                cfg.validate()

    def test_missing_mongodb_database(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "valid-and-sufficiently-long-secret-key-prod",
                "MONGODB_URI": "mongodb://localhost:27017",
                "MONGODB_DATABASE": "",
                "MONGO_DB_NAME": "",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="MONGODB_DATABASE must be set in production"):
                cfg.validate()

    def test_invalid_production_port(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "valid-and-sufficiently-long-secret-key-prod",
                "MONGODB_URI": "mongodb://localhost:27017",
                "MONGODB_DATABASE": "prod_db",
                "PORT": "70000",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="PORT must be between 1 and 65535"):
                cfg.validate()

    def test_invalid_production_max_content_length(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "valid-and-sufficiently-long-secret-key-prod",
                "MONGODB_URI": "mongodb://localhost:27017",
                "MONGODB_DATABASE": "prod_db",
                "MAX_CONTENT_LENGTH": "-1",
            },
        ):
            cfg = get_config("production")
            with pytest.raises(ValueError, match="MAX_CONTENT_LENGTH must be a positive integer"):
                cfg.validate()

    def test_create_app_fails_fast_on_invalid_production(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "short",
            },
        ):
            with pytest.raises(ValueError, match="Production configuration validation failed"):
                create_app("production")


@pytest.mark.unit
class TestSecretProtectionAndMasking:
    """Test masking utilities to ensure secrets and credentials are not leaked."""

    def test_mask_secret(self) -> None:
        assert mask_secret(None) == "[NOT SET]"
        assert mask_secret("") == "[NOT SET]"
        assert mask_secret("1234") == "****"
        assert mask_secret("supersecretkey12345") == "supe...****"

    def test_mask_connection_uri(self) -> None:
        assert mask_connection_uri(None) == "[NOT SET]"
        assert mask_connection_uri("") == "[NOT SET]"

        # URI with credentials
        raw_uri = "mongodb://admin_user:super_secret_password@cluster0.mongodb.net/ota_db"
        masked = mask_connection_uri(raw_uri)
        assert "super_secret_password" not in masked
        assert masked == "mongodb://admin_user:****@cluster0.mongodb.net/ota_db"

        # URI without credentials
        clean_uri = "mongodb://localhost:27017"
        assert mask_connection_uri(clean_uri) == clean_uri

    def test_safe_summary_does_not_leak_secrets(self) -> None:
        BaseConfig.SECRET_KEY = "ultra-secret-key-123456"
        BaseConfig.MONGODB_URI = "mongodb://user:my_secret_pass@db.local:27017/ota"

        summary = BaseConfig.get_safe_summary()
        assert "ultra-secret-key-123456" not in str(summary)
        assert "my_secret_pass" not in str(summary)
        assert summary["SECRET_KEY"] == "ultr...****"
        assert summary["MONGODB_URI"] == "mongodb://user:****@db.local:27017/ota"


@pytest.mark.unit
class TestEnvironmentLoading:
    """Test local development vs non-local environment loading."""

    def test_load_environment_called_only_for_dev(self) -> None:
        with patch("app.config.load_dotenv") as mock_load_dotenv:
            # Production: should NOT call load_dotenv
            with patch.dict(os.environ, {"APP_ENV": "production"}):
                load_environment()
                mock_load_dotenv.assert_not_called()

            # Testing: should NOT call load_dotenv
            with patch.dict(os.environ, {"APP_ENV": "testing"}):
                load_environment()
                mock_load_dotenv.assert_not_called()

            # Development: should call load_dotenv
            with patch.dict(os.environ, {"APP_ENV": "development"}):
                load_environment()
                mock_load_dotenv.assert_called_once()
