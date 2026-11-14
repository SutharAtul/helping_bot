"""Centralized environment-based configuration for OTA RAG Bot backend."""

from __future__ import annotations

import os
import re
from typing import Any, Type
from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from .env file for local development only.

    In production and testing environments, configuration should be supplied
    via OS environment variables, container orchestration, or CI/CD pipelines.
    """
    app_env = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).strip().lower()
    if app_env not in ("production", "testing"):
        load_dotenv()


# Automatically invoke loader for local development environments
load_environment()


def mask_secret(value: str | None, visible_chars: int = 4) -> str:
    """Mask a secret string for safe logging and diagnostics."""
    if not value:
        return "[NOT SET]"
    if len(value) <= visible_chars:
        return "****"
    return f"{value[:visible_chars]}...****"


def mask_connection_uri(uri: str | None) -> str:
    """Mask credentials (username:password) in a connection URI."""
    if not uri:
        return "[NOT SET]"
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)


class BaseConfig:
    """Base application configuration containing shared defaults and type parsers."""

    APP_NAME: str = "ota-rag-bot"
    VERSION: str = "0.1.0"

    # Environment
    APP_ENV: str = "base"
    ENV: str = "base"
    DEBUG: bool = False
    TESTING: bool = False

    # Server configuration
    PORT: int = 5000
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB

    # Security
    SECRET_KEY: str = "dev-insecure-secret-key-change-in-production"

    # Logging
    LOG_LEVEL: str = "INFO"

    # MongoDB connection
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "ota_rag_db"
    MONGO_CONNECT_TIMEOUT_MS: int = 2000
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = 2000

    # Backwards compatibility aliases
    MONGO_URI: str = MONGODB_URI
    MONGO_DB_NAME: str = MONGODB_DATABASE

    @classmethod
    def load_from_env(cls) -> None:
        """Load and parse configuration values dynamically from OS environment variables."""
        cls.APP_NAME = os.getenv("APP_NAME", cls.APP_NAME)
        cls.APP_ENV = os.getenv("APP_ENV", os.getenv("FLASK_ENV", cls.APP_ENV)).strip().lower()
        cls.ENV = cls.APP_ENV

        # Parse PORT
        port_val = os.getenv("PORT")
        if port_val is not None:
            try:
                cls.PORT = int(port_val)
            except ValueError:
                cls.PORT = 5000

        # Parse MAX_CONTENT_LENGTH
        max_len_val = os.getenv("MAX_CONTENT_LENGTH")
        if max_len_val is not None:
            try:
                cls.MAX_CONTENT_LENGTH = int(max_len_val)
            except ValueError:
                cls.MAX_CONTENT_LENGTH = 16 * 1024 * 1024

        # Parse SECRET_KEY
        cls.SECRET_KEY = os.getenv("SECRET_KEY", cls.SECRET_KEY)

        # Parse LOG_LEVEL
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", cls.LOG_LEVEL).upper()

        # Parse MongoDB parameters (supporting primary MONGODB_* and fallback MONGO_*)
        cls.MONGODB_URI = os.getenv("MONGODB_URI", os.getenv("MONGO_URI", cls.MONGODB_URI))
        cls.MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", os.getenv("MONGO_DB_NAME", cls.MONGODB_DATABASE))
        cls.MONGO_URI = cls.MONGODB_URI
        cls.MONGO_DB_NAME = cls.MONGODB_DATABASE

        # Timeout settings
        timeout_val = os.getenv("MONGO_CONNECT_TIMEOUT_MS")
        if timeout_val is not None:
            try:
                cls.MONGO_CONNECT_TIMEOUT_MS = int(timeout_val)
            except ValueError:
                pass

        server_sel_val = os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS")
        if server_sel_val is not None:
            try:
                cls.MONGO_SERVER_SELECTION_TIMEOUT_MS = int(server_sel_val)
            except ValueError:
                pass

    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings. Overridden by environment-specific subclasses."""
        pass

    @classmethod
    def get_safe_summary(cls) -> dict[str, Any]:
        """Return configuration dictionary with secrets and credentials masked."""
        return {
            "APP_NAME": cls.APP_NAME,
            "APP_ENV": cls.APP_ENV,
            "DEBUG": cls.DEBUG,
            "TESTING": cls.TESTING,
            "PORT": cls.PORT,
            "MAX_CONTENT_LENGTH": cls.MAX_CONTENT_LENGTH,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "SECRET_KEY": mask_secret(cls.SECRET_KEY),
            "MONGODB_URI": mask_connection_uri(cls.MONGODB_URI),
            "MONGODB_DATABASE": cls.MONGODB_DATABASE,
        }


class DevelopmentConfig(BaseConfig):
    """Development environment configuration with debugging enabled."""

    APP_ENV: str = "development"
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    @classmethod
    def load_from_env(cls) -> None:
        super().load_from_env()
        cls.APP_ENV = "development"
        cls.ENV = "development"
        cls.DEBUG = True
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()


class TestingConfig(BaseConfig):
    """Testing environment configuration allowing tests without live dependencies."""

    APP_ENV: str = "testing"
    ENV: str = "testing"
    TESTING: bool = True
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    SECRET_KEY: str = "test-secret-key-12345"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "ota_rag_test_db"
    MONGO_URI: str = MONGODB_URI
    MONGO_DB_NAME: str = MONGODB_DATABASE

    @classmethod
    def load_from_env(cls) -> None:
        super().load_from_env()
        cls.APP_ENV = "testing"
        cls.ENV = "testing"
        cls.TESTING = True
        cls.DEBUG = True
        cls.LOG_LEVEL = "DEBUG"
        cls.SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-12345")
        cls.MONGODB_URI = os.getenv("MONGODB_TEST_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
        cls.MONGODB_DATABASE = os.getenv("MONGODB_TEST_DATABASE", os.getenv("MONGODB_DATABASE", "ota_rag_test_db"))
        cls.MONGO_URI = cls.MONGODB_URI
        cls.MONGO_DB_NAME = cls.MONGODB_DATABASE


class ProductionConfig(BaseConfig):
    """Production environment configuration with strict security validations."""

    APP_ENV: str = "production"
    ENV: str = "production"
    DEBUG: bool = False
    TESTING: bool = False
    LOG_LEVEL: str = "INFO"

    # Known insecure placeholders disallowed in production
    DISALLOWED_SECRETS: set[str] = {
        "dev-insecure-secret-key-change-in-production",
        "insecure-default-change-in-production",
        "replace-with-a-secure-random-secret-key",
        "replace-with-a-secure-random-secret-key-in-production",
        "your-development-secret-key-here",
        "test-secret-key-12345",
        "secret",
        "changeme",
        "password",
        "admin",
    }

    @classmethod
    def load_from_env(cls) -> None:
        super().load_from_env()
        cls.APP_ENV = "production"
        cls.ENV = "production"
        cls.DEBUG = False
        cls.TESTING = False
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    @classmethod
    def validate(cls) -> None:
        """Validate required production configuration at startup.

        Raises:
            ValueError: If any required setting is missing, placeholder, or insecure.
        """
        errors: list[str] = []

        # 1. Validate SECRET_KEY
        secret_key = (cls.SECRET_KEY or "").strip()
        if not secret_key:
            errors.append("SECRET_KEY must be set in production.")
        elif secret_key.lower() in cls.DISALLOWED_SECRETS:
            errors.append("SECRET_KEY is set to an insecure default/placeholder value.")
        elif len(secret_key) < 16:
            errors.append(
                f"SECRET_KEY is too short ({len(secret_key)} characters). Minimum length is 16."
            )

        # 2. Validate MONGODB_URI
        mongo_uri = (cls.MONGODB_URI or "").strip()
        if not mongo_uri:
            errors.append("MONGODB_URI must be set in production.")
        elif not (mongo_uri.startswith("mongodb://") or mongo_uri.startswith("mongodb+srv://")):
            errors.append(
                "MONGODB_URI must be a valid connection URI starting with 'mongodb://' or 'mongodb+srv://'."
            )

        # 3. Validate MONGODB_DATABASE
        mongo_db = (cls.MONGODB_DATABASE or "").strip()
        if not mongo_db:
            errors.append("MONGODB_DATABASE must be set in production.")

        # 4. Validate PORT
        if not (1 <= cls.PORT <= 65535):
            errors.append(f"PORT must be between 1 and 65535, got {cls.PORT}.")

        # 5. Validate MAX_CONTENT_LENGTH
        if cls.MAX_CONTENT_LENGTH <= 0:
            errors.append(
                f"MAX_CONTENT_LENGTH must be a positive integer in bytes, got {cls.MAX_CONTENT_LENGTH}."
            )

        if errors:
            raise ValueError(
                "Production configuration validation failed:\n  * " + "\n  * ".join(errors)
            )


CONFIG_MAP: dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> Type[BaseConfig]:
    """Retrieve and refresh configuration class by environment name."""
    if not env_name:
        env_name = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).strip().lower()

    config_cls = CONFIG_MAP.get(env_name.lower(), DevelopmentConfig)
    config_cls.load_from_env()
    return config_cls
