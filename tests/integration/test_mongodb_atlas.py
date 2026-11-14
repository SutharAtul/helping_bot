"""Optional live integration test for MongoDB Atlas connectivity.

Gated by the TEST_MONGODB_URI environment variable.
Required Environment Variables:
  - TEST_MONGODB_URI: Full MongoDB Atlas connection string (e.g. mongodb+srv://<user>:<password>@<cluster>.mongodb.net)
  - TEST_MONGODB_DATABASE (Optional, default: "ota_test_probe"): Dedicated test database name.

Safety Guarantees:
  - Production database names (e.g. "ota_rag_db", "*prod*", "*production*") are strictly blocked.
  - The probe only executes the admin "ping" command. No collections or documents are written or modified.
"""

from __future__ import annotations

import os
import pytest
from flask import Flask
from app.database.mongodb import MongoDB

TEST_URI = os.getenv("TEST_MONGODB_URI")
DISALLOWED_PROD_NAMES = {"ota_rag_db", "prod", "production", "live", "master"}


@pytest.mark.integration
@pytest.mark.skipif(
    not TEST_URI,
    reason="Live MongoDB Atlas integration test requires TEST_MONGODB_URI environment variable",
)
class TestLiveMongoDBAtlasIntegration:
    """Live connectivity verification against a real MongoDB Atlas cluster."""

    def test_live_atlas_connection_and_ping(self) -> None:
        target_db = os.getenv("TEST_MONGODB_DATABASE", "ota_test_probe").strip()

        # Safety Guard: Ensure test cannot target a production database
        if target_db.lower() in DISALLOWED_PROD_NAMES or "prod" in target_db.lower():
            pytest.fail(
                f"Safety violation: TEST_MONGODB_DATABASE cannot be '{target_db}'. "
                "Must use a dedicated non-production test database (e.g. 'ota_test_probe')."
            )

        app = Flask(__name__)
        app.config["MONGODB_URI"] = TEST_URI
        app.config["MONGODB_DATABASE"] = target_db
        app.config["MONGODB_SERVER_SELECTION_TIMEOUT_MS"] = 5000
        app.config["MONGODB_CONNECT_TIMEOUT_MS"] = 5000

        mongo = MongoDB()
        mongo.init_app(app)

        try:
            # Perform non-destructive connection verification
            status = mongo.check_connection()
            assert status["ok"] is True, f"Failed to connect to live MongoDB Atlas: {status}"
            assert status["status"] == "healthy"

            # Retrieve database reference and verify target database
            db = mongo.get_database()
            assert db is not None
            assert db.name == target_db
        finally:
            mongo.close()
