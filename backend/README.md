# OpenWahi backend

FastAPI service for OpenWahi, the open-source support agents harness for WhatsApp:
WhatsApp devices through GOWA, AI agents (LangChain/LangGraph) with RAG over
knowledge bases, webhook tools, a developer API, and an embeddable chat widget.

- **Auth:** Firebase Authentication. The frontend sends a Firebase ID token as
  `Authorization: Bearer <token>`; the backend verifies it with the Firebase Admin SDK.
  Server-to-server calls can use `X-API-Key: whapi_...` tokens from the developer portal.
- **Data:** PostgreSQL (SQLAlchemy async + Alembic), Qdrant (vectors), S3-compatible
  storage (MinIO by default) for knowledge-base files.
- **Side services:** `transcriber/` (voice notes) and `llamacpp/` (local LLM).

## Layout

```
app/
  config/      settings (pydantic-settings), database, Firebase init
  core/        auth dependencies, CSRF/Origin check, rate limiting, websockets
  modules/     auth, whatsapp, ai_assistant, rag_agent, knowledge_base, developer,
               widget, subscriptions, admin, items
  static/      widget.js (embeddable chat widget)
alembic/       migrations
tests/         pytest suite (real PostgreSQL, external services mocked)
```

Main route prefixes: `/auth`, `/whatsapp`, `/ai-assistant`, `/webhook-tools`,
`/knowledge-base`, `/developer`, `/widget`, `/subscriptions`, `/internal/admin`.
OpenAPI docs are at `/docs`; the developer API reference is at `/api-docs`.

## Configuration

All settings live in `app/config/settings.py` and are read from the environment or
`backend/.env`. `.env.example` lists every setting with local-development values.

Required: `FIREBASE_PROJECT_ID`, a Firebase service account JSON at
`FIREBASE_SERVICE_ACCOUNT_PATH` (default `/run/secrets/firebase-service-account.json`),
`DATABASE_URL`, and `AI_ENCRYPTION_KEY` (`uv run python generate_encryption_key.py`).

Notable options:

- `APP_NAME` — display name used in API titles and messages (default `OpenWahi`).
- `ADMIN_EMAILS` — comma-separated admin emails. The admin API under
  `/internal/admin/*` only accepts Firebase users whose email is verified and listed;
  if the list is empty, it returns 404 to everyone. `GET /auth/me` reports `is_admin`.
- `ALLOWED_ORIGINS` — CORS and Origin-check allow-list.
- `TRANSCRIBER_URL`, `LLAMACPP_BASE_URL`, `QDRANT_*`, `S3_*`, `EMBEDDING_*`.

Plans (`free`, `pro`, `enterprise`) are assigned by an administrator from the admin
panel. The plan sets the WhatsApp device limit (1 / 10 / 100); `pro` users run on the
platform-managed AI provider chain (`MANAGED_AI_*`) with a monthly conversation cap
(`PRO_MONTHLY_CONVERSATION_LIMIT`). `GET /subscriptions/me` returns the plan and
device limit.

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Start the dependencies
from the repository root:

```bash
docker compose -f docker-compose.dev.yml up -d postgres qdrant minio minio-init whatsapp transcriber
```

Then, in `backend/`:

```bash
cp .env.example .env       # fill FIREBASE_PROJECT_ID, AI_ENCRYPTION_KEY, ...
make install               # uv sync --extra test
make migrate-up            # uv run alembic upgrade head
make dev                   # uvicorn on http://localhost:8000
```

Migrations: `make migrate-create MSG="describe change"` autogenerates a revision;
`uv run alembic check` confirms models and migrations agree. The Docker image runs
`alembic upgrade head` on start (`entrypoint.sh`).

## Tests

The suite needs a reachable PostgreSQL server; it creates the test database if missing.

```bash
make test-back
# or
TEST_DATABASE_URL=postgresql+asyncpg://openwahi:openwahi_dev_password@localhost:5432/openwahi_test \
  uv run pytest tests/ -q
```

`TEST_DATABASE_URL` defaults to the value above; the test database is created through
the `openwahi` database on the same server. Firebase, GOWA, Qdrant, S3 and LLM
providers are mocked.

Lint: `uv run --extra lint ruff check .`
