"""Application entry point for running locally or through WSGI servers."""

from __future__ import annotations

import os
from app.config import load_environment
from app import create_app

# Load .env for local development only
load_environment()

# Instantiate application for WSGI servers (e.g. Gunicorn)
env_name = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development"))
app = create_app(env_name)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(app.config.get("PORT", 5000))
    debug = bool(app.config.get("DEBUG", False))

    app.logger.info(f"Starting server on {host}:{port} (debug={debug}, env={app.config.get('APP_ENV')})")
    app.run(host=host, port=port, debug=debug)
