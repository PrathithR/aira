# AIRA — Codebase File Reference

Every file in the project, what it does, and how it connects to everything else.

---

## Core Application

### `src/main.py`

FastAPI application entry point.

**Implements:** FastAPI app instance (`app`), `GET /health` endpoint.

**Responsibilities:**
- Bootstrap the web server
- Expose health check for Docker/orchestration monitoring

**Uses:** `fastapi`
**Used by:** Dockerfile CMD (`uvicorn src.main:app`), docker-compose, test suite

---

### `src/settings.py`

Centralized configuration via Pydantic Settings. Singleton loaded at import time.

**Implements:**
- `Settings(BaseSettings)` — all application config fields:
  - `app_env`, `llm_provider`, `llm_model`, `llm_temperature`, `llm_max_tokens`
  - API keys: `gemini_api_key`, `anthropic_api_key`, `openai_api_key`
  - `max_tool_iterations`, `conversation_history_limit`
  - `ollama_base_url`
  - Google OAuth: `google_client_id`, `google_client_secret`, `google_redirect_uri`
  - `encryption_key`, `database_url`
  - ntfy: `ntfy_server`, `ntfy_topic`, `ntfy_default_priority`
  - Scheduler: `default_timezone`, `scheduler_misfire_grace_seconds`
  - Logging: `log_tool_calls`, `log_llm_responses`
- Properties:
  - `log_level` — derived from `app_env` (DEBUG for dev, WARNING for production), overridable via `LOG_LEVEL_OVERRIDE`
  - `require_confirmation_for_writes` — **hardcoded True**, not configurable
  - `allow_autonomous_writes` — **hardcoded False**, not configurable
  - `is_dev`, `is_production` — convenience booleans
  - `active_api_key` — returns API key for the selected LLM provider, raises if missing
- `settings` — module-level singleton instance

**Responsibilities:**
- Single source of truth for all config
- Load and validate `.env` at startup
- Enforce safety invariants (confirmation-before-write)

**Uses:** `pydantic_settings`, `functools.cached_property`
**Used by:** `src/encryption.py`, and will be used by every module in the project (agent, llm, services, db, api)

---

### `src/encryption.py`

Fernet symmetric encryption for sensitive data at rest (OAuth tokens, credentials).

**Implements:**
- `_fernet` — module-level cached Fernet instance
- `_get_fernet() -> Fernet` — lazy init, reads `settings.encryption_key`, raises if not set
- `encrypt(plaintext: str) -> str` — encrypts to base64-encoded ciphertext
- `decrypt(ciphertext: str) -> str` — decrypts back to plaintext

**Responsibilities:**
- Encrypt OAuth tokens before DB storage
- Decrypt tokens when needed for API calls
- Validate that encryption key is configured

**Uses:** `cryptography.fernet.Fernet`, `src.settings.settings`
**Used by:** DB layer (token storage), services layer (token retrieval)

---

## Agent Layer — `src/agent/`

Central reasoning controller. Orchestrates the ReAct decision loop.

**Status:** Scaffolded (empty `__init__.py` + architecture README)

**Planned responsibilities:**
- Build prompt context (history + system instructions)
- Inject tool definitions into LLM calls
- Call the LLM via `src/llm/`
- Interpret and validate tool call responses
- Execute tools via `src/tools/`
- Feed tool results back to the LLM
- Enforce `max_tool_iterations` limit
- Return final structured response

**Will not:** Handle HTTP/WebSockets, call external APIs directly, write to DB without validation, handle auth.

**Will use:** `src/llm/`, `src/tools/`, `src/settings.py`
**Will be used by:** `src/api/`

**Loop model:** Send -> Receive -> Execute Tool -> Feed Back -> Repeat -> Final Response

---

## LLM Layer — `src/llm/`

Thin abstraction over LiteLLM. Isolates model provider details from the agent.

**Status:** Scaffolded (README only, no `__init__.py` yet)

**Planned responsibilities:**
- Call LiteLLM with provider-specific config
- Handle API key injection
- Return structured model responses
- Centralize retries and logging
- Enable model switching via config

**Will not:** Execute tools, access DB, perform business logic.

**Will use:** `litellm`, `src/settings.py`
**Will be used by:** `src/agent/`

---

## Database Layer — `src/db/`

SQLAlchemy ORM models and database session management. Source of truth for persisted data.

**Status:** Scaffolded (empty `__init__.py` + architecture README)

**Planned responsibilities:**
- Define ORM models (OAuthToken, Task, Message, ActionLog)
- Create and manage async database sessions
- Store OAuth tokens (encrypted via `src/encryption.py`)
- Store tasks, chat history, user preferences
- Handle migrations via Alembic

**Will not:** Contain business logic, know about LLM providers, call external APIs.

**Will use:** `sqlalchemy`, `aiosqlite`, `alembic`, `src/encryption.py`, `src/settings.py`
**Will be used by:** `src/services/`, `src/agent/`

---

## Services Layer — `src/services/`

External API integration modules. Each service wraps one external system.

**Status:** Scaffolded (empty `__init__.py` + architecture README)

**Planned responsibilities:**
- Call external APIs (Google Calendar, Gmail, ntfy, etc.)
- Encrypt/decrypt tokens via `src/encryption.py`
- Normalize API responses into internal formats
- Handle API errors and retries
- Read/write to DB via `src/db/`

**Will not:** Contain LLM logic, build prompts, handle HTTP request/response objects.

**Will use:** `src/db/`, `src/encryption.py`, `src/settings.py`, `httpx`, Google API client libs
**Will be used by:** `src/tools/`

---

## Tools Layer — `src/tools/`

LLM-facing wrappers around services. The bridge between agent reasoning and real-world actions.

**Status:** Scaffolded (empty `__init__.py` + architecture README)

**Planned responsibilities:**
- Define tool metadata (name, description, parameter schema) for the LLM
- Validate arguments coming from LLM responses
- Call the appropriate service method
- Return normalized results back to the agent
- Classify tools as read (auto-execute) or write (require confirmation)

**Will not:** Build prompts, access HTTP routes, contain complex business logic.

**Will use:** `src/services/`, `src/settings.py`
**Will be used by:** `src/agent/`

---

## API Layer — `src/api/`

REST and WebSocket endpoint layer. Network boundary of AIRA.

**Status:** Scaffolded (README only, no `__init__.py` yet)

**Planned responsibilities:**
- Authenticate incoming requests
- Validate request/response bodies via Pydantic schemas
- Route requests to the agent layer
- Stream or return responses to clients
- Expose OAuth callback endpoint

**Will not:** Build prompts, call LiteLLM directly, execute tools, call external APIs, contain business logic.

**Flow:** Client -> API -> Agent -> API -> Client

**Will use:** `src/agent/`, `src/schema/`, `fastapi`
**Will be used by:** `src/main.py` (router registration)

---

## Schema Layer — `src/schema/`

Pydantic request/response models for the API layer.

**Status:** Empty directory (no files yet)

**Planned responsibilities:**
- Define Pydantic models for all API request and response bodies
- Define tool parameter schemas
- Define message/conversation schemas

**Will use:** `pydantic`
**Will be used by:** `src/api/`, `src/agent/`

---

## Configuration & Infrastructure

### `pyproject.toml`

Project metadata and dependency management.

**Defines:**
- Project: `aira` v0.1.0, Python >=3.11
- Production deps: FastAPI, Uvicorn, LiteLLM, APScheduler, SQLAlchemy, aiosqlite, Alembic, Google API clients, httpx, Pydantic, pydantic-settings, cryptography, Rich, Typer
- Dev deps: pytest, pytest-asyncio, ruff

**Used by:** Dockerfile (`pip install .`), any local install

---

### `Dockerfile`

Production container image.

**Defines:**
- Base: `python:3.11-slim`
- System deps: gcc, libffi-dev, curl, sqlite3
- Non-root user: `appuser` (uid 1000)
- Health check: `GET /health` every 30s
- CMD: `uvicorn src.main:app --host 0.0.0.0 --port 8000`

**Uses:** `pyproject.toml` (dependency install)
**Used by:** `docker-compose.yml`, `docker-compose.dev.yml`

---

### `docker-compose.yml`

Production orchestration.

**Defines:**
- Service `aira`: builds from Dockerfile, port 8000, persistent `aira-data` volume, loads `.env`, `restart: unless-stopped`

**Uses:** `Dockerfile`, `.env`

---

### `docker-compose.dev.yml`

Development orchestration with hot reload.

**Defines:**
- Same as production, plus:
  - Source mounts: `./src`, `./data`, `./scripts`, `./tests`
  - CMD override: adds `--reload` flag for live code reloading
  - `DEBUG=true`

**Uses:** `Dockerfile`, `.env`

---

### `.env.example`

Template for required environment variables. Users copy this to `.env` and fill in values.

**Documents:** APP_ENV, LLM API keys, Ollama URL, Google OAuth credentials, encryption key, database URL, ntfy config, timezone.

**Used by:** Developers during setup. Loaded by `src/settings.py` (as `.env`).

---

### `.gitignore`

Excludes from version control: `.env`, secrets, `__pycache__`, venv, `data/*` (except `.gitkeep`), IDE files, test/lint caches, OAuth credential files.

---

### `.dockerignore`

Excludes from Docker build context: `.git`, `.env`, secrets, Python artifacts, tests, docs, data, IDE files. Keeps the image small and secret-free.

---

## Package Init Files

All currently empty. Exist to mark directories as Python packages.

| File | Marks |
|---|---|
| `src/__init__.py` | `src` as package root |
| `src/agent/__init__.py` | `src.agent` |
| `src/db/__init__.py` | `src.db` |
| `src/services/__init__.py` | `src.services` |
| `src/tools/__init__.py` | `src.tools` |
| `tests/__init__.py` | `tests` |

---

## Dependency Graph

```
src/main.py
  └─ fastapi

src/settings.py
  └─ pydantic_settings

src/encryption.py
  ├─ cryptography
  └─ src/settings.py

src/api/          (future)
  ├─ src/agent/
  └─ src/schema/

src/agent/        (future)
  ├─ src/llm/
  ├─ src/tools/
  └─ src/settings.py

src/llm/          (future)
  ├─ litellm
  └─ src/settings.py

src/tools/        (future)
  ├─ src/services/
  └─ src/settings.py

src/services/     (future)
  ├─ src/db/
  ├─ src/encryption.py
  └─ src/settings.py

src/db/           (future)
  ├─ sqlalchemy
  ├─ src/encryption.py
  └─ src/settings.py
```

---

## Layer Flow

```
Client -> API -> Agent -> LLM
                   |
                 Tools -> Services -> DB
                                 |
                             External APIs
```
