# OpenWahi Frontend

Web UI for OpenWahi, the open-source support agents harness for WhatsApp. Built with Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS + shadcn/ui, TanStack Query and Firebase Authentication.

## Tech stack

- **Framework**: Next.js 15 (App Router), React 19, TypeScript 5.9
- **UI**: Tailwind CSS 3.4, shadcn/ui (Radix UI primitives), lucide-react icons
- **Data**: TanStack Query v5, Axios, native WebSockets for live WhatsApp events
- **Auth**: Firebase Authentication (Google sign-in)
- **i18n**: next-intl, Spanish (default) and English, locale-prefixed URLs (`/es/...`, `/en/...`)
- **Forms**: react-hook-form
- **Tests**: Vitest + Testing Library (jsdom)

## Requirements

- Node.js 20.19+
- pnpm 10.17.1 (`corepack enable` or `npx pnpm@10.17.1`)
- A running OpenWahi backend (see the repository root README)
- A Firebase project with the Google sign-in provider enabled

## Getting started

```bash
cd frontend
pnpm install
cp .env.example .env.local   # then fill in your Firebase web app config
pnpm dev
```

The app runs at http://localhost:3000. `/` redirects to `/<locale>/dashboard`; unauthenticated users are sent to the login page.

## Environment variables

`.env.example` is the complete catalog. All variables are `NEXT_PUBLIC_*`, so they are inlined into the browser bundle **at build time** — rebuild after changing them and never put secrets in them.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_APP_NAME` | No | `OpenWahi` | Display name used in the header, login page, page titles and admin panel |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend base URL for REST calls, WebSockets, API examples and widget snippets |
| `NEXT_PUBLIC_FRONTEND_URL` | No | request origin | Public URL of this frontend, used by the auth callback redirect |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Yes | – | Firebase web app config |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Yes | – | Firebase web app config |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Yes | – | Firebase web app config (must match the backend's service account project) |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Yes | – | Firebase web app config |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Yes | – | Firebase web app config |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Yes | – | Firebase web app config |
| `NEXT_PUBLIC_ALLOWED_EMAILS` | No | empty (everyone) | Comma-separated sign-in allowlist, checked client-side after Google sign-in |
| `NEXT_PUBLIC_DEV_BYPASS_AUTH` | No | `false` | Development only: use a Firebase ID token placed in `localStorage.fb_id_token` instead of the Google popup. Ignored in production builds |
| `NEXT_PUBLIC_AI_SANDBOX_TIMEOUT_MS` | No | `60000` | Per-request timeout for the AI assistant test sandbox |
| `NEXT_PUBLIC_SUPPORT_WIDGET_TOKEN` | No | empty (disabled) | Widget token that embeds this instance's own support chat widget on every page |
| `NEXT_PUBLIC_SUPPORT_WIDGET_TITLE` | No | `<APP_NAME> support` | Title of that support widget |

## Scripts

```bash
pnpm dev                  # Development server
pnpm build                # Production build
pnpm start                # Serve the production build
pnpm lint                 # ESLint (next lint)
pnpm test                 # Vitest unit tests
pnpm test:watch           # Vitest in watch mode
pnpm test:coverage        # Vitest with coverage
pnpm test:localized-404   # Runtime check of localized 404 pages (after `pnpm build`; port: LOCALIZED_404_TEST_PORT, default 4317)
```

## Authentication

- Users sign in with Google through Firebase Authentication (`src/config/firebase.ts`, `src/context/AuthContext.tsx`).
- The Firebase ID token is stored in `localStorage` (`fb_id_token`) and sent as `Authorization: Bearer <token>` by the Axios client (`src/tools/api/client.ts`). The backend verifies it with the Firebase Admin SDK.
- A `401` from the backend clears the session and dispatches the `openwahi:auth-unauthorized` event, which signs the user out.
- `AuthenticatedRouteGuard` keeps private pages (and their data hooks) unmounted until auth resolves and redirects anonymous visitors to `/<locale>/login`.
- The admin panel (`/<locale>/admin`) is only rendered when `GET /auth/me` returns `is_admin: true`. Admins are configured on the backend with `ADMIN_EMAILS`; everyone else gets a 404, and the backend enforces the same rule on `/internal/admin/*`.

## Routes

| Route | Private | Description |
|---|---|---|
| `/` | – | Redirects to `/dashboard` |
| `/login` | No | Google sign-in |
| `/auth/callback` | No | Fallback redirect after auth |
| `/dashboard` | Yes | Overview |
| `/items` | Yes | Example CRUD module |
| `/whatsapp-devices` | Yes | Link WhatsApp devices (QR), device limit per plan |
| `/whatsapp-chats` | Yes | Live inbox |
| `/ai-assistant` | Yes | Assistant configuration, test sandbox, embeddable widget |
| `/ai-assistant/tools` | Yes | Webhook tools the assistant can call |
| `/knowledge-base` | Yes | Knowledge bases and document uploads (RAG) |
| `/developer` | Yes | API tokens, outgoing webhooks, API examples |
| `/admin` | Admin | Users, operator-assigned plans, costs, AI provider chain |

## Project structure

```
src/
├── app/
│   ├── layout.tsx               # Root layout (passthrough)
│   ├── not-found.tsx            # Localized 404 for unmatched URLs
│   └── [locale]/                # Locale-prefixed routes (see table above)
│       ├── layout.tsx           # Providers: Intl, Query, Auth, route guard, optional support widget
│       └── metadata.ts          # Localized <title>/<meta> and favicon
├── components/                  # shadcn/ui primitives, Header, route guard
├── config/                      # brand.ts (APP_NAME), constants.ts (API_BASE_URL), firebase.ts
├── context/AuthContext.tsx      # Firebase session state
├── hooks/                       # use-toast
├── i18n/                        # next-intl routing and request config
├── lib/                         # Email allowlist, URL validation, utilities
├── middleware.ts                # next-intl locale routing
├── modules/                     # Feature modules: whatsapp, ai-assistant, knowledge-base,
│                                #   developer, items, subscription, admin
├── providers/QueryProvider.tsx  # TanStack Query client (singleton in the browser)
└── tools/                       # Axios client, token manager, auth events, shared hooks
messages/                        # en.json / es.json (keep both files in sync)
```

Each feature module follows `components/ → hooks/ → services/ → types.ts`; components call hooks, hooks wrap TanStack Query around the service functions, and services call the backend through the shared Axios client. WebSocket events for WhatsApp are merged into the query cache.

## Internationalization

- Locales: `es` (default) and `en`, always prefixed in the URL.
- Translations live in `messages/es.json` and `messages/en.json`; add every key to both files.

## Troubleshooting

- **`auth/invalid-api-key` or blank login page**: the `NEXT_PUBLIC_FIREBASE_*` values are missing or wrong. They are inlined at build time, so rebuild after fixing them.
- **Google popup closes without signing in**: add your frontend domain to *Authorized domains* in Firebase Authentication settings.
- **Every API call returns 401**: the backend's Firebase service account must belong to the same project as `NEXT_PUBLIC_FIREBASE_PROJECT_ID`.
- **WebSocket does not connect**: check `NEXT_PUBLIC_API_URL`, that the backend is running, and that the device belongs to the signed-in user.
- **`ChunkLoadError`**: `rm -rf .next node_modules/.cache && pnpm build`.
