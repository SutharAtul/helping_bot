# OTA RAG Bot Backend - Phase 1.1

Production-grade Flask backend foundation for an **Online Travel Agency (OTA) Retrieval-Augmented Generation (RAG) Bot**.

---

## 1. Overview & Architecture

This repository establishes the foundational backend architecture (**Phase 1.1 blueprint**) for the OTA RAG Bot. It provides a modular, production-ready structure built on Python 3.12+ and Flask using the **Application Factory Pattern**.

### Key Architectural Highlights
- **Application Factory Pattern**: `create_app()` enables clean environment switching (`development`, `testing`, `production`) and isolated test executions.
- **Strict Configuration Separation**: Driven by environment variables and `python-dotenv`, with dedicated configurations and no hardcoded secrets.
- **Resilient MongoDB Extension**: Custom `MongoExtension` wrapping PyMongo with non-blocking initialization, connection pooling, and health probing.
- **Pydantic Validation**: Strong request/response typing and serialization for health probes and API contracts.
- **Centralized Error Handling**: Standardized JSON error response envelope across all HTTP and domain exceptions.
- **Production Logging**: Structured console logging with timestamps, process IDs, log levels, and module origins.
- **Enterprise-ready Health Checks**: Dedicated liveness (`/live`) and readiness (`/ready`) endpoints designed for container orchestrators (Kubernetes/ECS).

---

## 2. Project Directory Structure

```text
helping_bot/
├── app/
│   ├── __init__.py              # Application factory (create_app)
│   ├── config.py                # Environment configuration classes
│   ├── extensions.py            # PyMongo extension wrapper
│   ├── api/
│   │   ├── __init__.py          # API package
│   │   └── v1/
│   │       ├── __init__.py      # Blueprint aggregation for v1
│   │       └── health.py        # Health, liveness, and readiness routes
│   ├── core/
│   │   ├── __init__.py          # Core package
│   │   ├── errors.py            # Custom exceptions & global error handlers
│   │   └── logging.py           # Structured production logging setup
│   ├── schemas/
│   │   ├── __init__.py          # Schemas package
│   │   └── health.py            # Pydantic schemas for health responses
│   ├── models/
│   │   └── __init__.py          # Database entities (future phases)
│   └── services/
│       └── __init__.py          # Domain business logic (future phases)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures (app, client, runner)
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py       # Configuration tests
│   │   └── test_errors.py       # Exception and error handler tests
│   └── integration/
│       ├── __init__.py
│       └── test_health.py       # API route and probe tests
├── .env.example                 # Template for environment configuration
├── .gitignore                   # Comprehensive ignore rules
├── pytest.ini                   # Pytest discovery and coverage configuration
├── requirements.txt             # Pinned dependency specifications
├── run.py                       # Application execution entry point
└── README.md                    # Project documentation
```

---

## 3. Prerequisites

- **Python**: Version `3.12+`
- **MongoDB**: Version `6.0+` or `7.0+` (local or remote MongoDB Atlas)
- **Virtual Environment Tool**: `venv` or `virtualenv`

---

## 4. Setup & Installation

### Step 1: Clone & Navigate to Repository
```bash
cd helping_bot
```

### Step 2: Create and Activate Virtual Environment

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the example environment file and customize your settings:
```bash
cp .env.example .env
```

Ensure `.env` contains:
```ini
FLASK_ENV=development
FLASK_DEBUG=True
APP_NAME=ota-rag-bot
HOST=0.0.0.0
PORT=5000
SECRET_KEY=generate-a-secure-random-key-for-local-dev
LOG_LEVEL=INFO
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=ota_rag_db
```

---

## 5. Running the Application

### Development Server
Run directly using the entry point:
```bash
python run.py
```
Or via the Flask CLI:
```bash
flask --app run:app run --host 0.0.0.0 --port 5000 --debug
```

### Production WSGI Server (Gunicorn)
For Linux/production deployments, start the application via Gunicorn:
```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 run:app
```

---

## 6. API Reference (Phase 1.1)

| Method | Endpoint | Description | Sample Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root service info | `200 OK` |
| `GET` | `/api/v1/health` | Comprehensive health check (app + MongoDB) | `200 OK` / `503 Service Unavailable` |
| `GET` | `/api/v1/health/live` | Liveness probe for process orchestrators | `200 OK` |
| `GET` | `/api/v1/health/ready` | Readiness probe verifying critical dependencies | `200 OK` / `503 Service Unavailable` |

### Sample Response (`GET /api/v1/health`)
```json
{
  "dependencies": {
    "mongodb": {
      "message": "Connected to cluster",
      "status": "healthy"
    }
  },
  "environment": "development",
  "service": "ota-rag-bot",
  "status": "healthy",
  "timestamp": "2026-11-14T07:22:15.123456Z",
  "version": "0.1.0"
}
```

### Error Response Envelope
```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "The requested URL was not found on the server",
    "details": {}
  }
}
```

---

## 7. Running Tests & Code Quality

Run the test suite with coverage reporting:
```bash
pytest
```

Run only unit tests:
```bash
pytest -m unit
```

Run only integration tests:
```bash
pytest -m integration
```

Generate HTML coverage report:
```bash
pytest --cov=app --cov-report=html
```

---

## 8. Phase Roadmap

- [x] **Phase 1.1**: Project setup, application factory, configuration, PyMongo extension, health endpoints, test harness.
- [ ] **Phase 1.2**: MongoDB schemas and indexing (hotel/flight collections, conversational sessions).
- [ ] **Phase 2.1**: Embedding pipeline and vector database integration.
- [ ] **Phase 2.2**: FAQ ingestion and semantic search CRUD.
- [ ] **Phase 3.1**: OTA Live API connectors (booking lookup, inventory checking).
- [ ] **Phase 3.2**: LLM RAG agent orchestration and guardrails.

