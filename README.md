# OpenWahi

**openwahi** es un harness de código abierto y autoalojable para operar agentes de soporte con IA en WhatsApp y en tu sitio web.

- **Canal de WhatsApp** mediante [GOWA](https://github.com/aldinokemal/go-whatsapp-web-multidevice), una pasarela multidispositivo de WhatsApp Web: conecta uno o varios números escaneando un código QR.
- **Bases de conocimiento RAG**: sube documentos; se dividen en fragmentos, se vectorizan localmente (sentence-transformers) y se guardan en [Qdrant](https://qdrant.tech).
- **Agente LangGraph** que responde a partir de tu base de conocimiento y puede llamar a tus sistemas mediante **herramientas webhook** configurables (crear tickets, consultar pedidos, agendar reuniones, …).
- **Widget web embebible**: una sola etiqueta `<script>` pone el mismo agente en cualquier sitio web.
- **Panel de administración** para quien opera la instancia: estadísticas de uso, usuarios y sus planes (límite de dispositivos), costos de IA y la cadena gestionada de proveedores de IA.
- **IA local primero**: un servidor llama.cpp incluido ejecuta un modelo pequeño en CPU; Groq y AWS Bedrock son opcionales. Las notas de voz las transcribe un servicio Whisper local.

> [!WARNING]
> **Protocolo de WhatsApp no oficial.** GOWA automatiza el protocolo de *WhatsApp Web*. **No** es la plataforma oficial WhatsApp Business (Cloud API). Usarlo puede infringir los Términos de Servicio de WhatsApp y **los números conectados pueden ser restringidos o bloqueados de forma permanente**. Usa números que puedas permitirte perder, respeta las políticas de WhatsApp y la ley local (consentimiento, nada de spam) y evalúa el riesgo antes de depender de él. openwahi y GOWA **no están afiliados, respaldados ni patrocinados por Meta Platforms, Inc. ni WhatsApp LLC**; "WhatsApp" es una marca registrada de su titular.

## Arquitectura

```
  Visitantes de la web       Operadores (navegador)          Usuarios de WhatsApp
        │                            │                              │
  widget.js (<script>)      Frontend Next.js (:3000)          WhatsApp Web
        │                     Firebase Auth (Google)                │
        │                            │                        ┌─────┴──────┐
        └────────── HTTPS ───────────┼────────────────────────│   GOWA     │
                                     ▼                  webhook│ (whatsapp) │
                         ┌──────────────────────────┐◄─────────└────────────┘
                         │   Backend FastAPI (:8000) │── envía mensajes ──►
                         │  agente LangGraph · RAG   │
                         │  tools webhook · widget   │──── HTTP ────► tus webhooks
                         └──┬──────┬──────┬──────┬───┘
                            │      │      │      │
                     PostgreSQL  Qdrant  S3 /   llama.cpp      transcriber
                      (datos) (vectores) MinIO  (LLM local)  (Whisper, notas de voz)
```

| Componente | Ruta | Tecnología |
|---|---|---|
| API backend | `backend/` | Python 3.12, FastAPI, SQLAlchemy 2 (async) + Alembic, LangChain/LangGraph, `uv` |
| Frontend | `frontend/` | Next.js 15 (App Router), React 19, TypeScript, Tailwind + shadcn/ui, TanStack Query, next-intl (en/es), `pnpm` |
| Transcriptor | `transcriber/` | FastAPI + faster-whisper (Groq Whisper opcional) |
| LLM local | `llamacpp/` | Servidor llama.cpp con un modelo GGUF Qwen3.5 0.8B |
| Orquestación | `docker-compose.*.yml` | postgres, qdrant, minio (+ creación del bucket), whatsapp (GOWA), transcriber, backend, llamacpp |

## Inicio rápido (desarrollo local)

Requisitos: Docker con Compose v2, Node.js ≥ 20.19 con `pnpm`, Python 3 (solo para generar una clave) y una cuenta de Google para Firebase.

### 1. Crea un proyecto de Firebase

openwahi usa Firebase Authentication (inicio de sesión con Google) para las cuentas de operador.

1. En la [consola de Firebase](https://console.firebase.google.com), crea un proyecto.
2. **Authentication → Sign-in method**: habilita **Google**. `localhost` viene autorizado por defecto; agrega tu dominio de producción más adelante.
3. **Project settings → General → Your apps**: agrega una **Web app** y copia sus valores de configuración (`apiKey`, `authDomain`, `projectId`, …) para el frontend.
4. **Project settings → Service accounts → Generate new private key**: guarda el archivo JSON como

   ```bash
   mkdir -p secrets
   mv ~/Downloads/<clave-descargada>.json secrets/firebase-service-account.json
   ```

   `secrets/` está en `.gitignore`. Nunca subas este archivo al repositorio.

### 2. Configura y arranca el backend

```bash
cp .env.dev.example .env.dev
```

Edita `.env.dev`:

- `FIREBASE_PROJECT_ID`: el id de tu proyecto de Firebase.
- `AI_ENCRYPTION_KEY`: genera una clave Fernet:
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  (`pip install cryptography` si hace falta).
- `ADMIN_EMAILS` (opcional): el correo de tu cuenta de Google para habilitar el panel de administración.

Luego:

```bash
make dev
```

La primera compilación descarga el modelo local (~1 GB), así que tarda un rato. Cuando esté arriba, la documentación de la API queda en http://localhost:8000/docs. Todos los puertos están en [docs/deployment/docker.md](docs/deployment/docker.md).

### 3. Arranca el frontend

```bash
cd frontend
cp .env.example .env.local   # completa NEXT_PUBLIC_FIREBASE_* con los valores del paso 1.3
pnpm install
pnpm dev
```

Abre http://localhost:3000, inicia sesión con Google y luego:

1. **Dispositivos** → agrega un dispositivo y escanea el código QR con el teléfono que hará de agente.
2. **Base de Conocimiento** → crea una base y sube documentos.
3. **Asistente de IA** → configura el agente (prompt, modelo, base de conocimiento, herramientas webhook) y pruébalo en el sandbox.
4. Opcional: copia el snippet del **widget** para poner el agente en un sitio web.

## Embeber el widget

```html
<script src="https://your-backend.example.com/static/widget.js"
        data-widget-token="wgt_..."></script>
```

Atributos opcionales: `data-title`, `data-placeholder`, `data-primary-color`, `data-secondary-color`, `data-position` (`right`/`left`), `data-dark`. Si el script se inyecta dinámicamente, define `window.__OPENWAHI_TOKEN__` y `window.__OPENWAHI_BACKEND_URL__` (y opcionalmente `__OPENWAHI_TITLE__`, `__OPENWAHI_DARK__`) antes de cargarlo.

## Configuración

Toda la configuración son variables de entorno con valores por defecto seguros para desarrollo local. Los archivos de ejemplo son el catálogo completo y comentado:

| Archivo | Lo usa | Lo más importante |
|---|---|---|
| [`.env.dev.example`](.env.dev.example) | `docker-compose.dev.yml` (`make dev`) | Proyecto de Firebase + ruta de la cuenta de servicio, `AI_ENCRYPTION_KEY`, `ADMIN_EMAILS`, `APP_NAME`, Postgres, almacenamiento S3, Qdrant Cloud opcional, credenciales de GOWA, llama.cpp/Groq, puertos del host |
| [`.env.prod.example`](.env.prod.example) | `docker-compose.prod.yml` (`make prod`) | El mismo conjunto con marcadores `CHANGE_ME`; `ALLOWED_ORIGINS` para el dominio de tu frontend; `BACKEND_PORT` enlazado a `127.0.0.1` |
| [`frontend/.env.example`](frontend/.env.example) | Frontend Next.js | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_FIREBASE_*`, `NEXT_PUBLIC_APP_NAME`, token opcional del widget de soporte |
| [`backend/.env.example`](backend/.env.example) | Backend fuera de Docker | Catálogo de ajustes del backend |

Variables clave:

| Variable | Valor por defecto | Para qué sirve |
|---|---|---|
| `APP_NAME` / `NEXT_PUBLIC_APP_NAME` | `OpenWahi` | Nombre visible en la API, la interfaz y el widget |
| `ADMIN_EMAILS` | vacío (admin deshabilitado) | Correos verificados por Firebase, separados por comas, con acceso al panel de administración |
| `AI_ENCRYPTION_KEY` | — (obligatoria) | Clave Fernet que cifra las claves de proveedores y los secretos guardados |
| `QDRANT_URL`, `QDRANT_API_KEY` | vacío (qdrant incluido) | Usar un clúster remoto de Qdrant en su lugar |
| `S3_ENDPOINT_URL`, `S3_*` | almacenamiento compatible con MinIO incluido | Cualquier almacenamiento compatible con S3 (AWS S3, Cloudflare R2, …) |
| `GROQ_API_KEY` | vacío | Respaldo opcional de inferencia y transcripción alojadas |

## Producción

`make prod` levanta los mismos servicios desde `docker-compose.prod.yml` y solo expone el backend en `127.0.0.1`. Pon delante un proxy inverso con TLS, despliega el frontend en cualquier host de Node.js con `NEXT_PUBLIC_API_URL` apuntando a la URL pública del backend y haz copias de seguridad de los volúmenes de Docker. Detalles: [docs/deployment/docker.md](docs/deployment/docker.md).

## Documentación

- [Despliegue con Docker](docs/deployment/docker.md)
- [Integraciones con webhooks](docs/integrations/webhook-examples.md)
- [Guía para contribuidores y agentes](AGENTS.md)
- [Política de seguridad](SECURITY.md)

## Licencia

openwahi se distribuye bajo la [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). Si ejecutas una versión modificada como servicio en red, debes ofrecer a sus usuarios el código fuente correspondiente.

Los componentes de terceros (GOWA, Qdrant, PostgreSQL, la imagen de almacenamiento compatible con MinIO, llama.cpp y los pesos de los modelos) se distribuyen bajo sus propias licencias.
