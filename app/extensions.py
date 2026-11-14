"""Extensions module for initializing third-party integrations."""

from __future__ import annotations

import logging
from typing import Optional
from flask import Flask
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class MongoExtension:
    """Production-ready PyMongo extension wrapper for Flask."""

    def __init__(self, app: Optional[Flask] = None) -> None:
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize MongoDB client with Flask app configuration."""
        uri: str = app.config.get("MONGODB_URI") or app.config.get("MONGO_URI", "mongodb://localhost:27017")
        db_name: str = app.config.get("MONGODB_DATABASE") or app.config.get("MONGO_DB_NAME", "ota_rag_db")
        timeout_ms: int = app.config.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", 2000)
        connect_timeout_ms: int = app.config.get("MONGO_CONNECT_TIMEOUT_MS", 2000)

        # Initialize MongoClient lazily (connect=False prevents blocking on app startup)
        self.client = MongoClient(
            uri,
            connect=False,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=connect_timeout_ms,
        )
        self.db = self.client[db_name]
        app.extensions["pymongo"] = self

        @app.teardown_appcontext
        def teardown_mongo(exception: Optional[BaseException] = None) -> None:
            # PyMongo manages connection pooling internally; no action needed per request
            pass

    def get_db(self) -> Database:
        """Retrieve active MongoDB database instance."""
        if self.db is None:
            raise RuntimeError("MongoExtension is not initialized. Ensure init_app() was called.")
        return self.db

    def ping(self) -> bool:
        """Ping MongoDB cluster to verify connectivity."""
        if self.client is None:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except (PyMongoError, Exception) as exc:
            logger.warning("MongoDB ping failed. Dependency may be unreachable.")
            return False

    def close(self) -> None:
        """Close MongoDB connection pool."""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None


mongo = MongoExtension()
