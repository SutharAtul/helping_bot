"""Robust MongoDB Atlas connection and management layer using official PyMongo driver."""

from __future__ import annotations

import logging
from typing import Any, Optional
from flask import Flask, current_app, has_app_context
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, PyMongoError, ServerSelectionTimeoutError
from app.config import mask_connection_uri

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when MongoDB connection or operation fails without leaking secrets."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        safe_message = mask_connection_uri(message)
        super().__init__(safe_message)
        self.message = safe_message
        self.details = details or {}


class DatabaseNotInitializedError(DatabaseConnectionError):
    """Raised when database access is attempted before extension initialization."""

    def __init__(
        self,
        message: str = "MongoDB extension has not been initialized. Ensure init_app() was called.",
    ) -> None:
        super().__init__(message)


class MongoDB:
    """Production-grade MongoDB manager for Flask applications.

    Key Features:
    - Thread-safe MongoClient reuse with managed connection pooling.
    - Cloud/Atlas-optimized connection and server selection timeouts.
    - Configuration reading exclusively from Flask app.config.
    - Credential-sanitized diagnostic output and error envelopes.
    - Comprehensive support for mocking and dependency injection.
    - Graceful connection termination and context cleanup.
    """

    def __init__(
        self,
        app: Optional[Flask] = None,
        client: Optional[MongoClient] = None,
    ) -> None:
        self._client: Optional[MongoClient] = client
        self._database: Optional[Database] = None
        self._app: Optional[Flask] = None

        if app is not None:
            self.init_app(app, client=client)

    def init_app(
        self,
        app: Flask,
        client: Optional[MongoClient] = None,
    ) -> None:
        """Initialize MongoDB with Flask application configuration."""
        self._app = app

        # Read configuration exclusively from Flask application config
        uri: str = (
            app.config.get("MONGODB_URI")
            or app.config.get("MONGO_URI")
            or "mongodb://localhost:27017"
        )
        db_name: str = (
            app.config.get("MONGODB_DATABASE")
            or app.config.get("MONGO_DB_NAME")
            or "ota_rag_db"
        )

        # Timeout & connection pool configurations (optimized for MongoDB Atlas)
        connect_timeout_ms = int(app.config.get("MONGODB_CONNECT_TIMEOUT_MS", 5000))
        server_selection_timeout_ms = int(
            app.config.get("MONGODB_SERVER_SELECTION_TIMEOUT_MS", 5000)
        )
        socket_timeout_ms = int(app.config.get("MONGODB_SOCKET_TIMEOUT_MS", 10000))
        max_pool_size = int(app.config.get("MONGODB_MAX_POOL_SIZE", 50))
        min_pool_size = int(app.config.get("MONGODB_MIN_POOL_SIZE", 5))

        if client is not None:
            # Dependency injection of client (e.g. for testing / mocking)
            self._client = client
        else:
            # Reusable MongoClient with connection pooling and non-blocking startup
            self._client = MongoClient(
                uri,
                connect=False,
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                socketTimeoutMS=socket_timeout_ms,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                appname=app.config.get("APP_NAME", "ota-rag-bot"),
            )

        self._database = self._client[db_name]

        # Register extension in Flask application registry
        app.extensions["mongodb"] = self
        app.extensions["pymongo"] = self

        # Teardown hook
        @app.teardown_appcontext
        def teardown_mongo_context(exception: Optional[BaseException] = None) -> None:
            # PyMongo manages thread-safe socket pooling; no per-request disconnect needed
            pass

    def get_client(self) -> MongoClient:
        """Return the active MongoClient instance."""
        if self._client is None:
            raise DatabaseNotInitializedError()
        return self._client

    def get_database(self) -> Database:
        """Return the active Database instance."""
        if self._database is None:
            raise DatabaseNotInitializedError()
        return self._database

    @property
    def db(self) -> Database:
        """Convenience property for accessing the database."""
        return self.get_database()

    def get_db(self) -> Database:
        """Compatibility method for accessing the database."""
        return self.get_database()

    def ping(self) -> bool:
        """Run an admin ping command to verify connectivity."""
        status_info = self.check_connection()
        return status_info["ok"]

    def check_connection(self) -> dict[str, Any]:
        """Perform a structured ping check with sanitized diagnostic output."""
        if self._client is None:
            return {
                "ok": False,
                "status": "uninitialized",
                "message": "MongoDB client is not initialized.",
            }

        try:
            self._client.admin.command("ping")
            return {
                "ok": True,
                "status": "healthy",
                "message": "Connected to MongoDB cluster.",
            }
        except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
            safe_err = mask_connection_uri(str(exc))
            logger.warning(f"MongoDB ping failed (unreachable/timeout): {safe_err}")
            return {
                "ok": False,
                "status": "unreachable",
                "message": "MongoDB cluster is unreachable or timed out.",
                "details": safe_err,
            }
        except PyMongoError as exc:
            safe_err = mask_connection_uri(str(exc))
            logger.warning(f"MongoDB ping failed (database operation error): {safe_err}")
            return {
                "ok": False,
                "status": "error",
                "message": "MongoDB operation error.",
                "details": safe_err,
            }
        except Exception as exc:
            safe_err = mask_connection_uri(str(exc))
            logger.error(f"Unexpected error during MongoDB ping: {type(exc).__name__} - {safe_err}")
            return {
                "ok": False,
                "status": "error",
                "message": "Unexpected error while communicating with MongoDB.",
                "details": safe_err,
            }

    def close(self) -> None:
        """Gracefully close the MongoClient connection pool."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:
                logger.warning(f"Error while closing MongoClient: {type(exc).__name__}")
            finally:
                self._client = None
                self._database = None


def get_mongo_db() -> Database:
    """Dependency helper to obtain the MongoDB Database from the current application context."""
    if not has_app_context():
        raise DatabaseNotInitializedError("No active Flask application context.")
    mongo_ext: Optional[MongoDB] = current_app.extensions.get("mongodb")
    if mongo_ext is None:
        raise DatabaseNotInitializedError("MongoDB extension not registered on current application.")
    return mongo_ext.get_database()
