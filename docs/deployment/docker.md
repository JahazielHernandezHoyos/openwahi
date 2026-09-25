# Running openwahi with Docker Compose

The repository ships two self-contained stacks. Neither needs a SaaS account besides a Firebase project for authentication.

| File | Purpose |
|---|---|
| `docker-compose.dev.yml` | Development: hot reload for backend and transcriber, every service published on the host, separate `*-dev` volumes. |
| `docker-compose.prod.yml` | Production: backend runs migrations then `uvicorn --workers 4`; only the backend is published, on `127.0.0.1`; persistent `*-prod` volumes. |

Both stacks run the same services:

| Service | Image / build | Role |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Main database |
| `qdrant` | `qdrant/qdrant` | Vector store for RAG |
| `minio` | `pgsty/silo` (community MinIO fork) | S3-compatible storage for knowledge-base files |
| `minio-init` | same image, one-shot | Creates the `S3_BUCKET_NAME` bucket, then exits |
| `whatsapp` | `aldinokemal2104/go-whatsapp-web-multidevice` (GOWA) | WhatsApp Web gateway; sends events to `backend:8000/whatsapp/webhook` |
| `transcriber` | `./transcriber` | Voice-note transcription (local Whisper, optional Groq) |
| `backend` | `./backend` | FastAPI API, agent, widget endpoints |
| `llamacpp` | `./llamacpp` | Local CPU LLM server (OpenAI-compatible) |

The Next.js frontend is not part of Compose; run it with `pnpm` (see the root README) or deploy it to any Node.js host.

## Configuration

Configuration lives in an env file passed with `--env-file`. The example files list **every** variable the matching compose file reads:

```bash
cp .env.dev.example .env.dev     # development
cp .env.prod.example .env.prod   # production
```

`.env.dev` and `.env.prod` are ignored by Git; only the `.example` templates are versioned.

Required before the first start:

1. **Firebase service account.** Download the Admin SDK key (Firebase console → Project settings → Service accounts → Generate new private key) and save it as `secrets/firebase-service-account.json`, or point `FIREBASE_SERVICE_ACCOUNT_FILE` to another host path. The file is mounted read-only at `/run/secrets/firebase-service-account.json`. `secrets/` is git-ignored.
2. **`FIREBASE_PROJECT_ID`**: your Firebase project id.
3. **`AI_ENCRYPTION_KEY`**: a Fernet key. Keep it stable; changing it makes stored secrets unreadable.
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. Production only: replace every `CHANGE_ME` value and set `ALLOWED_ORIGINS` to your public frontend origin(s).

Validate the configuration without starting anything:

```bash
docker compose --env-file .env.dev  -f docker-compose.dev.yml  config -q
docker compose --env-file .env.prod -f docker-compose.prod.yml config -q
```

### Using external services

The bundled `qdrant` and `minio` services are the defaults. To use hosted services instead, override in your env file:

- **Qdrant Cloud**: set `QDRANT_URL` (full `https://` URL) and `QDRANT_API_KEY`.
- **S3 / Cloudflare R2 / any S3-compatible store**: set `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME` and `S3_REGION` (`auto` for R2). The bundled `minio` keeps running but is unused.

## Development

```bash
make dev          # docker compose --env-file .env.dev -f docker-compose.dev.yml up --build
make dev-down     # stop, keep volumes
make dev-logs     # follow logs
```

Published endpoints with the defaults from `.env.dev.example`:

| Service | URL |
|---|---|
| Backend / Swagger | http://localhost:8000/docs |
| PostgreSQL | `localhost:15432` |
| Qdrant | http://localhost:16333/dashboard |
| Object storage (S3 API) | http://localhost:19000 |
| Transcriber | http://localhost:18001 |
| WhatsApp gateway (GOWA) | http://localhost:3001 |
| llama.cpp | http://127.0.0.1:8080 |

The dev backend runs `alembic upgrade head` before starting `uvicorn --reload`, with `./backend` bind-mounted into the container.

To wipe all development data: `docker compose --env-file .env.dev -f docker-compose.dev.yml down -v`.

## Production

```bash
make prod         # docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
make prod-logs
make prod-down
```

- Only the backend is published, on `127.0.0.1:${BACKEND_PORT}` (default `8000`). Put a TLS reverse proxy (Caddy, nginx, Traefik, …) in front of it and point the frontend's `NEXT_PUBLIC_API_URL` at the public URL.
- PostgreSQL, Qdrant, object storage, GOWA, the transcriber and llama.cpp are reachable only inside the Compose network.
- `ALLOWED_ORIGINS` must list the public frontend origin(s), comma-separated. Websites embedding the chat widget do not need to be listed.
- Back up the named volumes `postgres-prod`, `qdrant-prod`, `minio-prod` and `whatsapp-prod` (the last one holds the WhatsApp session).
- Set `ADMIN_EMAILS` to enable the admin panel for specific, verified Firebase accounts.
