"""Application entry point for running locally or through WSGI servers."""

from __future__ import annotations

import os
from dotenv import load_dotenv
from app import create_app

# Ensure environment variables are loaded
load_dotenv()

# Instantiate application for WSGI servers (e.g. Gunicorn)
env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    app.logger.info(f"Starting server on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)

