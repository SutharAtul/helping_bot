"""Configuration module for OTA RAG Bot backend."""

from __future__ import annotations

import os
from typing import Type
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()


class BaseConfig:
    """Base application configuration."""

    APP_NAME: str = os.getenv("APP_NAME", "ota-rag-bot")
    VERSION: str = "0.1.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-default-change-in-production")
    
    # Server / Environment
    ENV: str = "base"
    DEBUG: bool = False
    TESTING: bool = False

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # PyMongo Configuration
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "ota_rag_db")
    MONGO_CONNECT_TIMEOUT_MS: int = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "2000"))
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "2000"))


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    ENV: str = "testing"
    TESTING: bool = True
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    MONGO_DB_NAME: str = os.getenv("MONGO_TEST_DB_NAME", "ota_rag_test_db")
    # In testing, use dummy key if none provided
    SECRET_KEY: str = "test-secret-key-12345"


class ProductionConfig(BaseConfig):
    """Production environment configuration."""

    ENV: str = "production"
    DEBUG: bool = False
    TESTING: bool = False
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self) -> None:
        super().__init__()
        # Enforce strong secret key in production
        if self.SECRET_KEY in ("insecure-default-change-in-production", ""):
            import warnings

            warnings.warn(
                "SECRET_KEY is using an insecure default value in production! Set SECRET_KEY via environment variable.",
                RuntimeWarning,
                stacklevel=2,
            )


CONFIG_MAP: dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> Type[BaseConfig]:
    """Retrieve configuration class by environment name."""
    if not env_name:
        env_name = os.getenv("FLASK_ENV", "development").lower()
    return CONFIG_MAP.get(env_name.lower(), DevelopmentConfig)

