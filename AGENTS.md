# AGENTS.md

Guide for contributors and coding agents working in this repository.

## Project

openwahi is an open-source, self-hostable support-agents harness: a LangGraph agent with RAG (Qdrant) and webhook tools, reachable over WhatsApp (via the GOWA WhatsApp Web gateway) and an embeddable web widget, managed from a Next.js web app. License: AGPL-3.0.

Monorepo layout:

| Path | What |
|---|---|
| `backend/` | FastAPI API (Python 3.12, `uv`) |
| `frontend/` | Next.js 15 web app (TypeScript, `pnpm`) |
| `transcriber/` | Voice-note transcription service (faster-whisper, optional Groq) |
| `llamacpp/` | Local CPU LLM image (llama.cpp server + Qwen3.5 0.8B GGUF) |
| `docker-compose.dev.yml` / `docker-compose.prod.yml` | Full stacks; configured by `.env.dev` / `.env.prod` |
| `docs/` | Deployment and integration docs |

## Services (Compose)

`postgres` (main DB) · `qdrant` (vectors) · `minio` + `minio-init` (S3-compatible storage, bucket bootstrap) · `whatsapp` (GOWA; posts events to `backend:8000/whatsapp/webhook`) · `transcriber` · `backend` · `llamacpp`.
The frontend runs outside Compose.

Every variable a compose file reads is listed in the matching `.env.*.example`. When you add or remove a `${VAR}` in a compose file, update the example file in the same change.

## Commands

### Full stack (from repo root)
```bash
cp .env.dev.example .env.dev   # once; fill FIREBASE_PROJECT_ID, AI_ENCRYPTION_KEY
make dev                       # docker compose --env-file .env.dev -f docker-compose.dev.yml up --build
make dev-down                  # stop (keeps volumes)
make prod                      # production stack from .env.prod
docker compose --env-file .env.dev -f docker-compose.dev.yml config -q   # validate compose + env
```
The dev backend applies migrations (`alembic upgrade head`) on start. API docs: http://localhost:8000/docs.

### Backend (`cd backend`)
```bash
make install                          # uv sync --extra test
make dev                              # uvicorn --reload on :8000 (reads backend/.env)
make test-back                        # pytest
uv run pytest tests/test_auth.py -v   # single file
make migrate-create MSG="add foo"     # autogenerate an Alembic revision
make migrate-up                       # alembic upgrade head
```
Tests need PostgreSQL; they read `TEST_DATABASE_URL` (default `postgresql+asyncpg://openwahi:openwahi_dev_password@localhost:5432/openwahi_test`). Lint: `uv run ruff check .` (CI runs ruff on `backend/**`).

### Frontend (`cd frontend`)
```bash
pnpm install
pnpm dev              # http://localhost:3000
pnpm build
pnpm lint
pnpm test             # vitest run
```
Env catalog: `frontend/.env.example` (copy to `.env.local`).

## Backend architecture (`backend/app/`)

- `main.py`: app factory, middleware (CORS, origin validation, rate limiting), router registration, public widget sub-app mounted at `/widget`, static files at `/static` (serves `widget.js`).
- `config/settings.py`: pydantic `Settings`; all configuration comes from env vars.
- `core/`: auth dependencies (`get_current_user`, `get_current_user_id`, `get_current_user_id_flexible` for Bearer **or** `X-API-Key`), Firebase token verification, rate limiting, WebSocket manager.
- `modules/`:
  - `auth/`: `/auth/me` (includes `is_admin`), `/auth/verify`.
  - `whatsapp/`: devices, messages, GOWA client, webhook ingestion, WebSocket broadcast.
  - `ai_assistant/`: agent configuration, providers (llama.cpp, Groq, Bedrock), LangGraph agent, per-user memory, webhook tools (`webhook_tools.py`, `webhook_config_router.py`).
  - `rag_agent/`: agentic RAG graph (plan → search → evaluate → synthesize).
  - `knowledge_base/`: uploads, chunking, embeddings, S3 storage, Qdrant search.
  - `widget/`: widget tokens (authenticated) and public chat endpoints.
  - `developer/`: API tokens (`whapi_…`) and outbound event webhooks.
  - `subscriptions/`: operator-assigned plans (`free`/`pro`/`enterprise`) and device limits.
  - `admin/`: operator panel API under `/internal/admin/*`, enabled only for verified emails in `ADMIN_EMAILS`.

### Module pattern

Each module has `models.py` (SQLAlchemy models + Pydantic schemas), `service.py` (business logic) and `router.py` (FastAPI routes). To add one:

1. Create `backend/app/modules/<name>/` with those files.
2. Import its models in `backend/alembic/env.py` so autogenerate sees them.
3. Register the router in `backend/app/main.py`.
4. `make migrate-create MSG="add <name>"`, review the generated revision, then `make migrate-up`.

Keep a single Alembic head; `alembic check` must report no drift between models and migrations.

## Frontend architecture (`frontend/src/`)

Data flow: component → hook → service → Axios client (`tools/api/client.ts`) → backend, with TanStack Query caching and WebSocket events written into the cache.

- `app/[locale]/`: next-intl routing; every route is prefixed with `/en` or `/es`.
- `modules/`: domain modules mirroring the backend (whatsapp, ai-assistant, knowledge-base, developer, admin, subscription).
- `middleware.ts`: locale routing and auth guard.
- `config/brand.ts`: display name from `NEXT_PUBLIC_APP_NAME`.
- `messages/en.json`, `messages/es.json`: translations; add keys to both.

## Conventions

- No hardcoded instance data: URLs, names, emails and credentials come from env vars with localhost defaults. Use `example.com` and `15551234567` in fixtures and docs.
- Never commit secrets (`.env.*`, `secrets/`, service-account JSON are git-ignored).
- Tests should check behavior, not copy text or wiring.
- User-facing strings go through i18n in the frontend.
