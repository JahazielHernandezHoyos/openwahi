# OpenWahi

**openwahi** is an open-source, self-hostable harness for running AI support agents on WhatsApp and on your website.

- **WhatsApp channel** through [GOWA](https://github.com/aldinokemal/go-whatsapp-web-multidevice), a WhatsApp Web multi-device gateway: connect one or more numbers by scanning a QR code.
- **RAG knowledge bases**: upload documents; they are chunked, embedded locally (sentence-transformers) and stored in [Qdrant](https://qdrant.tech).
- **LangGraph agent** that answers from your knowledge base and can call your systems through configurable **webhook tools** (create tickets, look up orders, book meetings, …).
- **Embeddable web widget**: one `<script>` tag puts the same agent on any website.
- **Admin panel** for the instance operator: usage stats, users and their plans (device limits), AI costs, and the managed AI provider chain.
- **Local-first AI**: a bundled llama.cpp server runs a small model on CPU; Groq and AWS Bedrock are optional. Voice notes are transcribed by a local Whisper service.

> [!WARNING]
> **Unofficial WhatsApp protocol.** GOWA automates the *WhatsApp Web* protocol. It is **not** the official WhatsApp Business Platform (Cloud API). Using it may violate WhatsApp's Terms of Service and **the connected numbers can be restricted or permanently banned**. Use numbers you can afford to lose, respect WhatsApp's policies and local law (consent, no spam), and evaluate the risk before relying on it. openwahi and GOWA are **not affiliated with, endorsed by, or sponsored by Meta Platforms, Inc. or WhatsApp LLC**; "WhatsApp" is a trademark of its owner.

## Architecture

```
  Website visitors           Operators (browser)             WhatsApp users
        │                            │                              │
  widget.js (<script>)      Next.js frontend (:3000)          WhatsApp Web
        │                     Firebase Auth (Google)                │
        │                            │                        ┌─────┴──────┐
        └────────── HTTPS ───────────┼────────────────────────│   GOWA     │
                                     ▼                  webhook│ (whatsapp) │
                         ┌──────────────────────────┐◄─────────└────────────┘
                         │   FastAPI backend (:8000) │─── send messages ──►
                         │  LangGraph agent · RAG    │
                         │  webhook tools · widget   │──── HTTP ────► your webhooks
                         └──┬──────┬──────┬──────┬───┘
                            │      │      │      │
                     PostgreSQL  Qdrant  S3 /   llama.cpp      transcriber
                      (data)   (vectors) MinIO  (local LLM)  (Whisper, voice notes)
```

| Component | Path | Tech |
|---|---|---|
| Backend API | `backend/` | Python 3.12, FastAPI, SQLAlchemy 2 (async) + Alembic, LangChain/LangGraph, `uv` |
| Frontend | `frontend/` | Next.js 15 (App Router), React 19, TypeScript, Tailwind + shadcn/ui, TanStack Query, next-intl (en/es), `pnpm` |
| Transcriber | `transcriber/` | FastAPI + faster-whisper (optional Groq Whisper) |
| Local LLM | `llamacpp/` | llama.cpp server with a Qwen3.5 0.8B GGUF model |
| Orchestration | `docker-compose.*.yml` | postgres, qdrant, minio (+ bucket init), whatsapp (GOWA), transcriber, backend, llamacpp |

## Quickstart (local development)

Prerequisites: Docker with Compose v2, Node.js ≥ 20.19 with `pnpm`, Python 3 (only to generate a key), and a Google account for Firebase.

### 1. Create a Firebase project

openwahi uses Firebase Authentication (Google sign-in) for operator accounts.

1. In the [Firebase console](https://console.firebase.google.com), create a project.
2. **Authentication → Sign-in method**: enable **Google**. `localhost` is an authorized domain by default; add your production domain later.
3. **Project settings → General → Your apps**: add a **Web app** and copy its config values (`apiKey`, `authDomain`, `projectId`, …) for the frontend.
4. **Project settings → Service accounts → Generate new private key**: save the JSON file as

   ```bash
   mkdir -p secrets
   mv ~/Downloads/<downloaded-key>.json secrets/firebase-service-account.json
   ```

   `secrets/` is git-ignored. Never commit this file.

### 2. Configure and start the backend stack

```bash
cp .env.dev.example .env.dev
```

Edit `.env.dev`:

- `FIREBASE_PROJECT_ID`: your Firebase project id.
- `AI_ENCRYPTION_KEY`: generate a Fernet key:
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  (`pip install cryptography` if needed.)
- `ADMIN_EMAILS` (optional): your Google account email to enable the admin panel.

Then:

```bash
make dev
```

The first build downloads the local model (~1 GB), so it takes a while. When it is up, the API docs are at http://localhost:8000/docs. See [docs/deployment/docker.md](docs/deployment/docker.md) for all ports.

### 3. Start the frontend

```bash
cd frontend
cp .env.example .env.local   # fill in NEXT_PUBLIC_FIREBASE_* from step 1.3
pnpm install
pnpm dev
```

Open http://localhost:3000, sign in with Google, then:

1. **WhatsApp devices** → add a device and scan the QR code with the phone that will act as the agent.
2. **Knowledge base** → create a base and upload documents.
3. **AI assistant** → configure the agent (prompt, model, knowledge base, webhook tools) and test it in the sandbox.
4. Optionally get the **widget** snippet to embed the agent on a website.

## Embedding the widget

```html
<script src="https://your-backend.example.com/static/widget.js"
        data-widget-token="wgt_..."></script>
```

Optional attributes: `data-title`, `data-placeholder`, `data-primary-color`, `data-secondary-color`, `data-position` (`right`/`left`), `data-dark`. When the script is injected dynamically, set `window.__OPENWAHI_TOKEN__`, `window.__OPENWAHI_BACKEND_URL__` (and optionally `__OPENWAHI_TITLE__`, `__OPENWAHI_DARK__`) before loading it.

## Configuration

All configuration is environment variables with safe local defaults. The example files are the complete, commented catalogs:

| File | Used by | Highlights |
|---|---|---|
| [`.env.dev.example`](.env.dev.example) | `docker-compose.dev.yml` (`make dev`) | Firebase project + service-account path, `AI_ENCRYPTION_KEY`, `ADMIN_EMAILS`, `APP_NAME`, Postgres, S3 storage, optional Qdrant Cloud, GOWA credentials, llama.cpp/Groq, host ports |
| [`.env.prod.example`](.env.prod.example) | `docker-compose.prod.yml` (`make prod`) | Same set with `CHANGE_ME` placeholders; `ALLOWED_ORIGINS` for your frontend domain; `BACKEND_PORT` bound to `127.0.0.1` |
| [`frontend/.env.example`](frontend/.env.example) | Next.js frontend | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_FIREBASE_*`, `NEXT_PUBLIC_APP_NAME`, optional support widget token |
| [`backend/.env.example`](backend/.env.example) | Backend run outside Docker | Backend settings catalog |

Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` / `NEXT_PUBLIC_APP_NAME` | `OpenWahi` | Display name in the API, UI and widget |
| `ADMIN_EMAILS` | empty (admin disabled) | Comma-separated, Firebase-verified emails allowed into the admin panel |
| `AI_ENCRYPTION_KEY` | — (required) | Fernet key encrypting stored provider keys and secrets |
| `QDRANT_URL`, `QDRANT_API_KEY` | empty (bundled qdrant) | Use a remote Qdrant cluster instead |
| `S3_ENDPOINT_URL`, `S3_*` | bundled MinIO-compatible store | Any S3-compatible storage (AWS S3, Cloudflare R2, …) |
| `GROQ_API_KEY` | empty | Optional hosted inference/transcription fallback |

## Production

`make prod` starts the same services from `docker-compose.prod.yml` with only the backend exposed on `127.0.0.1`. Put a TLS reverse proxy in front of it, deploy the frontend to any Node.js host with `NEXT_PUBLIC_API_URL` pointing to the public backend URL, and back up the Docker volumes. Details: [docs/deployment/docker.md](docs/deployment/docker.md).

## Documentation

- [Docker deployment](docs/deployment/docker.md)
- [Webhook integrations](docs/integrations/webhook-examples.md)
- [Contributor and agent guide](AGENTS.md)
- [Security policy](SECURITY.md)

## License

openwahi is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). If you run a modified version as a network service, you must offer its users the corresponding source code.

Third-party components (GOWA, Qdrant, PostgreSQL, the MinIO-compatible storage image, llama.cpp and model weights) are distributed under their own licenses.
