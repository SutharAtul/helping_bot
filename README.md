# OTA RAG Bot Backend - Centralized Configuration

Production-grade Flask backend foundation for an **Online Travel Agency (OTA) Retrieval-Augmented Generation (RAG) Bot**.

---

## 1. Architectural Overview

The backend uses Flask with the **Application Factory Pattern** (`create_app()`) and a **Centralized Environment-based Configuration** system:

- **Environment-Specific Profiles**: Clean separation between `DevelopmentConfig`, `TestingConfig`, and `ProductionConfig` inheriting from `BaseConfig`.
- **12-Factor Compliant**: In production and testing, configurations are derived strictly from environment variables. Local `.env` files are loaded via `python-dotenv` for local development only.
- **Fail-Fast Startup Validation**: In production mode (`APP_ENV=production`), required security and infrastructure settings (`SECRET_KEY`, `MONGODB_URI`, `MONGODB_DATABASE`, `PORT`, `MAX_CONTENT_LENGTH`) are rigorously validated before the app boots.
- **Strict Secret Protection**: Sensitive credentials (such as `SECRET_KEY` and credentials in `MONGODB_URI`) are masked and never exposed in application logs, error responses, or health probes.
- **Dependency Isolation**: Testing profiles (`TestingConfig`) allow the complete test suite to execute reliably without requiring an active MongoDB cluster.

---

## 2. Configuration Reference

All settings can be configured using environment variables:

| Variable | Type | Default Value | Environments | Description |
| :--- | :--- | :--- | :--- | :--- |
| `APP_ENV` | `string` | `development` | All | Application environment profile: `development`, `testing`, or `production`. |
| `SECRET_KEY` | `string` | *dev placeholder* | All | Cryptographic key for session signing and tokens. **Required in production** ($\ge 16$ chars, non-placeholder). |
| `MONGODB_URI` | `string` | `mongodb://localhost:27017` | All | MongoDB connection URI (`mongodb://` or `mongodb+srv://`). **Required in production**. |
| `MONGODB_DATABASE`| `string` | `ota_rag_db` | All | Target MongoDB database name. **Required in production**. |
| `LOG_LEVEL` | `string` | `INFO` (`DEBUG` in dev/test) | All | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `PORT` | `integer`| `5000` | All | HTTP server listening port ($1 \le \text{port} \le 65535$). |
| `MAX_CONTENT_LENGTH`| `integer`| `16777216` (16 MB) | All | Maximum allowed request body size in bytes. |

*Note: For backward compatibility, `MONGO_URI` and `MONGO_DB_NAME` are supported as fallbacks for `MONGODB_URI` and `MONGODB_DATABASE`.*

---

## 3. Environment Behavior & Startup Validation

### Local Development (`APP_ENV=development`)
- Automatically loads environment variables from `.env` via `load_environment()`.
- Debug mode is enabled (`DEBUG=True`).
- Safe default credentials are used for development convenience if `.env` is omitted.

### Automated Testing (`APP_ENV=testing`)
- `.env` file loading is automatically skipped to prevent polluting test state.
- `TESTING=True` and `DEBUG=True`.
- Targets `ota_rag_test_db`.
- Tests run with non-blocking MongoDB extensions (`connect=False`), allowing full test execution without a live MongoDB database.

### Production (`APP_ENV=production`)
- `.env` file loading is explicitly disabled; all configuration must be provided via the host/container environment.
- Debug mode is disabled (`DEBUG=False`).
- **Startup Validation**: `ProductionConfig.validate()` executes during `create_app()`. The application will raise a `ValueError` and fail to boot if:
  - `SECRET_KEY` is not set, matches known insecure placeholders, or is fewer than 16 characters.
  - `MONGODB_URI` is not set or does not begin with `mongodb://` or `mongodb+srv://`.
  - `MONGODB_DATABASE` is not set or empty.
  - `PORT` is not within $1 - 65535$.
  - `MAX_CONTENT_LENGTH` is $\le 0$.

---

## 4. Secret Masking & Protection

To prevent accidental credential leakage in observability tools or client responses:
- `mask_secret(val)` masks keys (e.g. `supersecretkey` $\rightarrow$ `supe...****`).
- `mask_connection_uri(uri)` redacts basic authentication credentials in URIs (e.g. `mongodb://admin:pass@host:27017/db` $\rightarrow$ `mongodb://admin:****@host:27017/db`).
- Health probes (`/api/v1/health`) return only high-level status flags (`healthy`, `unreachable`), omitting connection strings or database names.
- Error handlers return sanitized JSON envelopes with no raw tracebacks or secret parameters.

---

## 5. Local Setup Instructions

### 1. Clone & Setup Virtual Environment
```bash
cd helping_bot
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Setup Local Environment Variables
Create your local `.env` from the provided template:
```bash
cp .env.example .env
```
*(The `.env` file is excluded in `.gitignore` to prevent committing secrets).*

### 4. Run the Application
**Development Server:**
```bash
python run.py
```
**Production Server (Gunicorn):**
```bash
APP_ENV=production \
SECRET_KEY="production-secret-key-at-least-16-chars" \
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net" \
MONGODB_DATABASE="ota_prod" \
gunicorn --workers 4 --bind 0.0.0.0:5000 run:app
```

---

## 6. Testing

Run all unit and integration tests:
```bash
pytest
```

Run only configuration unit tests:
```bash
pytest tests/unit/test_config.py -v
```

Generate coverage report:
```bash
pytest --cov=app --cov-report=term-missing
```
