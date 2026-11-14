"""Unit tests for MongoDB connection and manager layer using mocks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from flask import Flask
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError, ServerSelectionTimeoutError
from app.database.mongodb import (
    DatabaseConnectionError,
    DatabaseNotInitializedError,
    MongoDB,
    get_mongo_db,
)


@pytest.mark.unit
class TestMongoDBManager:
    """Test suite for MongoDB manager initialization, lifecycle, and operations."""

    def test_uninitialized_database_access_raises_error(self) -> None:
        mongo = MongoDB()
        with pytest.raises(DatabaseNotInitializedError):
            mongo.get_database()

        with pytest.raises(DatabaseNotInitializedError):
            mongo.get_client()

        with pytest.raises(DatabaseNotInitializedError):
            _ = mongo.db

        with pytest.raises(DatabaseNotInitializedError):
            mongo.get_db()

        # Ping when uninitialized returns False without raising
        assert mongo.ping() is False
        status = mongo.check_connection()
        assert status["ok"] is False
        assert status["status"] == "uninitialized"

    def test_init_app_reads_config_and_reuses_client(self) -> None:
        app = Flask(__name__)
        app.config["MONGODB_URI"] = "mongodb://cluster-mock.net:27017"
        app.config["MONGODB_DATABASE"] = "custom_test_db"
        app.config["MONGODB_CONNECT_TIMEOUT_MS"] = 3000
        app.config["MONGODB_SERVER_SELECTION_TIMEOUT_MS"] = 4000
        app.config["MONGODB_SOCKET_TIMEOUT_MS"] = 8000
        app.config["MONGODB_MAX_POOL_SIZE"] = 25
        app.config["MONGODB_MIN_POOL_SIZE"] = 2

        with patch("app.database.mongodb.MongoClient") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value = mock_client_instance

            mongo = MongoDB()
            mongo.init_app(app)

            # Assert MongoClient instantiated with exact configs
            mock_client_cls.assert_called_once_with(
                "mongodb://cluster-mock.net:27017",
                connect=False,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=3000,
                socketTimeoutMS=8000,
                maxPoolSize=25,
                minPoolSize=2,
                appname="ota-rag-bot",
            )

            # Assert single client reuse
            client1 = mongo.get_client()
            client2 = mongo.get_client()
            assert client1 is client2
            assert client1 is mock_client_instance

            # Assert database selection & properties
            db = mongo.get_database()
            assert mongo.db is db
            assert mongo.get_db() is db
            mock_client_instance.__getitem__.assert_called_with("custom_test_db")

            # Assert extension registered in Flask app
            assert app.extensions["mongodb"] is mongo
            assert app.extensions["pymongo"] is mongo

    def test_init_app_fallback_when_config_unavailable(self) -> None:
        app = Flask(__name__)
        # Empty config should safely fall back to defaults without crashing
        with patch("app.database.mongodb.MongoClient") as mock_client_cls:
            mongo = MongoDB()
            mongo.init_app(app)
            mock_client_cls.assert_called_once()
            call_args, call_kwargs = mock_client_cls.call_args
            assert call_args[0] == "mongodb://localhost:27017"
            assert call_kwargs["serverSelectionTimeoutMS"] == 5000

    def test_dependency_injection_custom_client(self) -> None:
        app = Flask(__name__)
        app.config["MONGODB_DATABASE"] = "injected_db"

        mock_injected_client = MagicMock()

        # Inject client directly via constructor
        mongo = MongoDB(app=app, client=mock_injected_client)

        assert mongo.get_client() is mock_injected_client
        _ = mongo.get_database()
        mock_injected_client.__getitem__.assert_called_with("injected_db")

    def test_ping_success(self) -> None:
        mock_client = MagicMock()
        mock_client.admin.command.return_value = {"ok": 1.0}

        mongo = MongoDB(client=mock_client)
        mongo._database = MagicMock()

        assert mongo.ping() is True
        status = mongo.check_connection()
        assert status["ok"] is True
        assert status["status"] == "healthy"
        mock_client.admin.command.assert_called_with("ping")

    def test_ping_server_selection_timeout_safe_error(self) -> None:
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = ServerSelectionTimeoutError("Server unreachable at secret-host")

        mongo = MongoDB(client=mock_client)
        assert mongo.ping() is False

        status = mongo.check_connection()
        assert status["ok"] is False
        assert status["status"] == "unreachable"
        # Ensure raw error details with host/secrets are sanitized
        assert "secret-host" not in status["message"]

    def test_ping_connection_failure_safe_error(self) -> None:
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = ConnectionFailure("Authentication failed: user:pass@atlas")

        mongo = MongoDB(client=mock_client)
        assert mongo.ping() is False

        status = mongo.check_connection()
        assert status["ok"] is False
        assert status["status"] == "unreachable"
        assert "pass@atlas" not in status["message"]

    def test_ping_generic_pymongo_error_safe_error(self) -> None:
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = OperationFailure("Operation not permitted on cluster")

        mongo = MongoDB(client=mock_client)
        assert mongo.ping() is False

        status = mongo.check_connection()
        assert status["ok"] is False
        assert status["status"] == "error"
        assert status["message"] == "MongoDB operation error."

    def test_ping_unexpected_exception_safe_error(self) -> None:
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = RuntimeError("Unexpected internal system issue")

        mongo = MongoDB(client=mock_client)
        assert mongo.ping() is False

        status = mongo.check_connection()
        assert status["ok"] is False
        assert status["status"] == "error"
        assert status["message"] == "Unexpected error while communicating with MongoDB."

    def test_close_clean_shutdown(self) -> None:
        mock_client = MagicMock()
        mongo = MongoDB(client=mock_client)
        mongo._database = MagicMock()

        mongo.close()
        mock_client.close.assert_called_once()
        assert mongo._client is None
        assert mongo._database is None

        # Subsequent access raises not initialized error
        with pytest.raises(DatabaseNotInitializedError):
            mongo.get_database()

    def test_close_handles_close_exception_gracefully(self) -> None:
        mock_client = MagicMock()
        mock_client.close.side_effect = RuntimeError("Socket disconnect failure")
        mongo = MongoDB(client=mock_client)
        mongo._database = MagicMock()

        # Should not raise exception
        mongo.close()
        assert mongo._client is None
        assert mongo._database is None

    def test_get_mongo_db_helper_with_active_context(self) -> None:
        app = Flask(__name__)
        app.config["MONGODB_DATABASE"] = "helper_test_db"
        mock_client = MagicMock()
        mongo = MongoDB(app=app, client=mock_client)

        with app.app_context():
            db = get_mongo_db()
            assert db is not None
            mock_client.__getitem__.assert_called_with("helper_test_db")

    def test_get_mongo_db_helper_without_context_raises_error(self) -> None:
        with patch("app.database.mongodb.has_app_context", return_value=False):
            with pytest.raises(DatabaseNotInitializedError, match="No active Flask application context"):
                get_mongo_db()

    def test_get_mongo_db_helper_without_extension_registered(self) -> None:
        app = Flask(__name__)
        # App context without MongoDB extension registered
        with app.app_context():
            with pytest.raises(DatabaseNotInitializedError, match="MongoDB extension not registered"):
                get_mongo_db()

    def test_database_connection_error_masks_credentials(self) -> None:
        raw_error_message = (
            "Failed connecting to mongodb+srv://app_user:super_secret_pw123@atlas-cluster.net/ota_db"
        )
        err = DatabaseConnectionError(raw_error_message)
        assert "super_secret_pw123" not in str(err)
        assert "super_secret_pw123" not in err.message
        assert "mongodb+srv://app_user:****@atlas-cluster.net/ota_db" in str(err)
