# OTA RAG Bot Backend - Phase 1 Architecture

Production-grade Flask backend foundation for an **Online Travel Agency (OTA) Retrieval-Augmented Generation (RAG) Bot**.

---

## 1. Architectural Overview

The backend uses Flask with the **Application Factory Pattern** (`create_app()`), a **Centralized Environment-based Configuration** system, and a dedicated **MongoDB Atlas Connection Layer**:

- **Environment-Specific Profiles**: Clean separation between `DevelopmentConfig`, `TestingConfig`, and `ProductionConfig` inheriting from `BaseConfig`.
- **12-Factor Compliant**: In production and testing, configurations are derived strictly from environment variables. Local `.env` files are loaded via `python-dotenv` for local development only.
- **Fail-Fast Startup Validation**: In production mode (`APP_ENV=production`), required security and infrastructure settings (`SECRET_KEY`, `MONGODB_URI`, `MONGODB_DATABASE`, `PORT`, `MAX_CONTENT_LENGTH`) are rigorously validated before the app boots.
- **Robust MongoDB Atlas Layer (`app/database/mongodb.py`)**:
  - Reuses a single thread-safe `MongoClient` with managed connection pooling (`maxPoolSize=50`, `minPoolSize=5`).
  - Cloud-optimized timeouts (`serverSelectionTimeoutMS=5000`, `connectTimeoutMS=5000`, `socketTimeoutMS=10000`).
  - Reads connection parameters exclusively from Flask application configuration.
  - Sanitizes connection URIs and credentials from all error messages and health logs.
  - Supports dependency injection and mocking for unit and integration testing.
  - Graceful connection termination via `close()` on shutdown.
- **Strict Secret Protection**: Sensitive credentials (`SECRET_KEY` and passwords in `MONGODB_URI`) are masked and never exposed in logs, error responses, or health probes.
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
| `MONGODB_CONNECT_TIMEOUT_MS`| `integer`| `5000` | All | Timeout in ms for establishing initial connection to MongoDB. |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS`| `integer`| `5000` | All | Timeout in ms for server/primary selection before erroring out. |
| `MONGODB_SOCKET_TIMEOUT_MS`| `integer`| `10000` | All | Socket read/write timeout in ms. |
| `MONGODB_MAX_POOL_SIZE`| `integer`| `50` | All | Maximum number of concurrent connections in the pool. |
| `MONGODB_MIN_POOL_SIZE`| `integer`| `5` | All | Minimum number of idle connections maintained in the pool. |
| `LOG_LEVEL` | `string` | `INFO` (`DEBUG` in dev/test) | All | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `PORT` | `integer`| `5000` | All | HTTP server listening port ($1 \le \text{port} \le 65535$). |
| `MAX_CONTENT_LENGTH`| `integer`| `16777216` (16 MB) | All | Maximum allowed request body size in bytes. |

*Note: For backward compatibility, `MONGO_URI` and `MONGO_DB_NAME` remain supported as fallbacks for `MONGODB_URI` and `MONGODB_DATABASE`.*

---

## 3. MongoDB Atlas Setup Guide

To connect the application to a cloud-hosted MongoDB Atlas cluster:

### A. Network Access Configuration (IP Whitelist)
1. In the MongoDB Atlas Console, navigate to **Security** $\rightarrow$ **Network Access**.
2. Click **Add IP Address**:
   - For local development: Click **Add Current IP Address** (or configure your development static IP / VPN).
   - For containerized / cloud hosting (e.g. AWS ECS, GCP Cloud Run, Render): Add your outbound NAT gateway static IPs or VPC CIDR block.
   - For staging/ephemeral environments: You may allow `0.0.0.0/0` temporarily, provided strong user authentication is enforced.
3. Wait for the status indicator to turn green (`Active`).

### B. Database User Permissions (Least Privilege)
1. In MongoDB Atlas, navigate to **Security** $\rightarrow$ **Database Access**.
2. Click **Add New Database User**:
   - **Authentication Method**: Password (SCRAM-SHA-256).
   - **Username**: E.g. `ota_rag_app_user`.
   - **Password**: Generate a secure 24+ character password.
3. Under **Database User Privileges**:
   - Grant **Built-in Role**: `Read and write to any database` or select **Specific Privileges** $\rightarrow$ `readWrite` on the target database (e.g., `ota_rag_db`).
   - **Do not** assign administrative roles (`atlasAdmin`, `readWriteAnyDatabase` in production) to application services.

### C. Connection String Setup
1. In Atlas, go to **Deployment** $\rightarrow$ **Database**, find your cluster, and click **Connect**.
2. Select **Drivers** (Python / 3.12+).
3. Copy the SRV connection string:
   ```text
   mongodb+srv://<username>:<password>@<cluster-name>.mongodb.net/<database>?retryWrites=true&w=majority
   ```
4. **Special Character Escaping**: If your password contains special characters (such as `@`, `:`, `/`, `?`, `#`, `&`), URL-encode them:
   ```python
   from urllib.parse import quote_plus
   encoded_password = quote_plus("my@secret#pass!")
   ```
5. Place the URI in your local `.env` file or production environment variable store:
   ```ini
   MONGODB_URI=mongodb+srv://ota_rag_app_user:ENCODED_PASSWORD@cluster0.abcde.mongodb.net/ota_rag_db?retryWrites=true&w=majority
   MONGODB_DATABASE=ota_rag_db
   ```

---

## 4. Secret Masking & Protection

To guarantee zero credential leakage in observability tools, logs, or client responses:
- `mask_secret(val)` redacts sensitive keys (e.g. `secret-key-12345` $\rightarrow$ `secr...****`).
- `mask_connection_uri(uri)` replaces basic authentication passwords with asterisks (e.g. `mongodb+srv://user:secret@cluster.net/db` $\rightarrow$ `mongodb+srv://user:****@cluster.net/db`).
- `DatabaseConnectionError` automatically passes error messages through `mask_connection_uri()`.
- Health probes (`/api/v1/health`) return only high-level status flags (`healthy`, `unreachable`), omitting connection strings or user identities.
- Global error handlers return sanitized JSON envelopes with no raw tracebacks or secret parameters.

---

## 5. Local Setup Instructions

### 1. Clone & Setup Virtual Environment
```bash
cd helping_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell
# source .venv/bin/activate     # Linux / macOS
```

### 2. Install Dependencies
```bash
python -m pip install --upgrade pip
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
**Production Server (Gunicorn on Linux):**
```bash
APP_ENV=production \
SECRET_KEY="production-secret-key-at-least-16-chars" \
MONGODB_URI="mongodb+srv://app_user:pass@cluster.mongodb.net" \
MONGODB_DATABASE="ota_rag_db" \
gunicorn --workers 4 --bind 0.0.0.0:5000 run:app
```

---

## 6. Testing

### Run All Unit and Integration Tests (Mocked)
```powershell
python -m pytest
```

### Run Only Database Unit Tests
```powershell
python -m pytest tests/unit/test_mongodb.py -v
```

### Run Live MongoDB Atlas Integration Test (Optional)
The live cluster integration test is gated and only executes when `TEST_MONGODB_URI` is explicitly provided:

**Windows PowerShell:**
```powershell
$env:TEST_MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net"
python -m pytest tests/integration/test_mongodb_atlas.py -v
```

**Linux / macOS:**
```bash
TEST_MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net" python -m pytest tests/integration/test_mongodb_atlas.py -v
```
