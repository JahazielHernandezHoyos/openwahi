import logging
import os

import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.firebase import initialize_firebase
from app.config.settings import settings
from app.core.csrf_protection import OriginValidationMiddleware
from app.core.middleware import ServerTimingMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.exceptions.handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.modules.admin.router import router as admin_router
from app.modules.ai_assistant.router import router as ai_assistant_router
from app.modules.ai_assistant.webhook_config_router import (
    router as webhook_tools_router,
)
from app.modules.auth.router import router as auth_router
from app.modules.developer.router import router as developer_router
from app.modules.items.router import router as items_router
from app.modules.knowledge_base.router import router as knowledge_base_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.whatsapp.router import router as whatsapp_router
from app.modules.widget.router import auth_router as widget_auth_router
from app.modules.widget.router import public_router as widget_public_router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Initialize Firebase Admin SDK
initialize_firebase()

# Initialize Sentry (must be done before FastAPI app initialization)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        # Performance Monitoring
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # Profiling (requires traces_sample_rate > 0)
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        # Environment tag for filtering in Sentry dashboard
        environment=settings.ENVIRONMENT,
        # Send default PII (user IPs, etc.) - set False if privacy is a concern
        send_default_pii=True,
        # Attach request data to errors
        enable_tracing=True,
    )
    logging.info(f"Sentry initialized for environment: {settings.ENVIRONMENT}")


# Initialize FastAPI app
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Open-source support agents harness",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Configure rate limiting
app.state.limiter = limiter

# Register middleware
# NOTE: do NOT add SlowAPIMiddleware here. In slowapi 0.1.10 the middleware runs
# _check_request_limit(..., in_middleware=True), which only evaluates the
# application-wide default limits and then sets request.state._rate_limiting_complete,
# causing the per-route @limiter.limit() decorators to skip their own check entirely.
app.add_middleware(ServerTimingMiddleware)

# Configure CORS with restricted methods and headers for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Webhook-Secret",
        "Accept",
        "Origin",
    ],
)

# Add Origin validation for CSRF-like protection on state-changing operations
# Note: Since we use JWT in headers (not cookies), traditional CSRF tokens aren't needed
# But we validate Origin to prevent unauthorized cross-origin requests
app.add_middleware(
    OriginValidationMiddleware,
    allowed_origins=settings.allowed_origins_list,
    strict_mode=settings.ENVIRONMENT == "production",  # Strict in production only
)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routes
app.include_router(auth_router)
app.include_router(items_router)
app.include_router(whatsapp_router)
app.include_router(ai_assistant_router)
app.include_router(webhook_tools_router)
app.include_router(knowledge_base_router)
app.include_router(developer_router)
app.include_router(subscriptions_router)
app.include_router(admin_router, prefix="/internal/admin")

# Widget management endpoints (authenticated, standard CORS)
app.include_router(widget_auth_router)

# Widget public sub-app (open CORS — allow_origins=["*"])
# Mounted at /widget so widget.js can POST to /widget/chat from any domain.
# public_router routes have NO /widget prefix themselves (added by mount).
widget_app = FastAPI(title=f"{settings.APP_NAME} Widget API (public)")
widget_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
widget_app.include_router(widget_public_router)
app.mount("/widget", widget_app)

# Serve static files (widget.js, etc.)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# ==================== Developer API Documentation (ReDoc) ====================


def get_developer_openapi_schema():
    """Generate OpenAPI schema filtered for developer endpoints only."""
    if not app.openapi_schema:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

    # Create a filtered schema for developer docs
    full_schema = app.openapi_schema.copy()

    # Filter paths to only include /whatsapp and /developer endpoints
    filtered_paths = {}
    for path, methods in full_schema.get("paths", {}).items():
        if path.startswith("/whatsapp") or path.startswith("/developer"):
            filtered_paths[path] = methods

    return {
        "openapi": full_schema.get("openapi", "3.1.0"),
        "info": {
            "title": "WhatsApp API - Developer Documentation",
            "version": full_schema.get("info", {}).get("version", "1.0.0"),
            "description": """
## WhatsApp API Documentation

Esta documentación cubre los endpoints disponibles para integrar WhatsApp en tus aplicaciones.

### Autenticación

La API soporta dos métodos de autenticación:

1. **Bearer Token (JWT)** - Para aplicaciones web con sesión de usuario
   ```
   Authorization: Bearer <jwt_token>
   ```

2. **API Key** - Para integraciones servidor a servidor
   ```
   X-API-Key: <your_api_token>
   ```

### Obtener un API Token

1. Ve al portal de desarrollador en tu aplicación
2. En la pestaña "API Tokens", genera un nuevo token
3. Copia el token (solo se muestra una vez)
4. Usa el token en el header `X-API-Key`

### Configurar Webhook

1. En el portal de desarrollador, ve a la pestaña "Webhook"
2. Ingresa la URL de tu webhook
3. Opcionalmente, configura un secreto para validar las firmas HMAC
4. Guarda la configuración

Cuando lleguen mensajes a tu WhatsApp, se enviarán a tu webhook con el siguiente formato:

```json
{
  "event": "message.received",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "message_id": "uuid",
    "device_id": "uuid",
    "from_phone": "573001234567",
    "body": "Hola!",
    "message_type": "text",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Si configuraste un secreto, el payload incluirá un header `X-Webhook-Signature` con la firma HMAC-SHA256.
""",
        },
        "paths": filtered_paths,
        "components": full_schema.get("components", {}),
    }


@app.get("/api-docs", include_in_schema=False)
async def developer_docs():
    """Serve ReDoc documentation for developer API."""
    return HTMLResponse(
        """
<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp API - Developer Docs</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <redoc spec-url='/api-docs/openapi.json'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
</body>
</html>
"""
    )


@app.get("/api-docs/openapi.json", include_in_schema=False)
async def developer_openapi():
    """Serve filtered OpenAPI schema for developer API."""
    return get_developer_openapi_schema()
