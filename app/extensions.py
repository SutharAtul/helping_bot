"""Extensions module for initializing third-party integrations."""

from __future__ import annotations

from app.database.mongodb import (
    MongoDB,
    get_mongo_db,
    DatabaseConnectionError,
    DatabaseNotInitializedError,
)

# Shared global MongoDB manager instance
mongo = MongoDB()

__all__ = [
    "mongo",
    "MongoDB",
    "get_mongo_db",
    "DatabaseConnectionError",
    "DatabaseNotInitializedError",
]
