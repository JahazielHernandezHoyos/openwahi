"""
Backend test configuration.

This conftest sets up:
1. A real PostgreSQL test database (TEST_DATABASE_URL, default openwahi_test)
2. Auto-creates/drops tables per test session
3. Mocks Firebase authentication
4. Provides an async HTTP client pointing at the FastAPI app
5. Mocks external services (GOWA, Qdrant, MinIO, Groq)

PostgreSQL must already be running, e.g. from the repo root:
    docker compose -f docker-compose.dev.yml up -d postgres

Usage:
    make test-back            # run backend tests
    make test-fast            # skip slow tests
    uv run pytest tests/ -v   # manual run
"""

import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend root is on sys.path so 'app' module resolves
BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..")
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# ---------------------------------------------------------------------------
# 1. Environment: set test env vars BEFORE importing the app
# ---------------------------------------------------------------------------
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://openwahi:openwahi_dev_password@localhost:5432/openwahi_test",
)

os.environ["FIREBASE_PROJECT_ID"] = "openwahi-test"
os.environ["AI_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "False"
os.environ["ADMIN_EMAILS"] = ""  # admin API disabled unless a test patches it
os.environ["WHATSAPP_WEBHOOK_SECRET"] = ""  # disable webhook secret validation
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["S3_ENDPOINT_URL"] = "http://localhost:9000"
os.environ["SENTRY_DSN"] = ""  # disable sentry in tests

# ---------------------------------------------------------------------------
# 2. Test database constants
# ---------------------------------------------------------------------------
# Maintenance connection on the same server, used to create the test database.
POSTGRES_ADMIN_DB = "openwahi"

# Fake user for authenticated requests
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_USER_PAYLOAD = {
    "sub": TEST_USER_ID,
    "email": "test@example.com",
    "role": "authenticated",
    "aud": "authenticated",
}


# ---------------------------------------------------------------------------
# 3. Ensure the test database exists
# ---------------------------------------------------------------------------
def _create_test_database():
    """Create the TEST_DATABASE_URL database if it doesn't exist."""
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    url = make_url(TEST_DB_URL)
    conn = psycopg2.connect(
        host=url.host or "localhost",
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        dbname=POSTGRES_ADMIN_DB,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,))
    if not cur.fetchone():
        cur.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(url.database), sql.Identifier(url.username)
            )
        )
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# 4. Session-scoped engine + table management
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine and tables once per session."""
    _create_test_database()

    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )

    # Import Base AFTER setting env vars so settings don't fail
    # CRITICAL: Set the test engine BEFORE creating tables, so any code
    # that lazily initializes the engine gets the test engine on the test event loop.
    from app.config.database import Base, set_engine
    from app.modules.ai_assistant.models import (  # noqa: F401
        AIConfigKnowledgeBase,
        WhatsAppAIConfigDB,
        WhatsAppAIConversationDB,
        WhatsAppAIMessageDB,
    )
    from app.modules.developer.models import ApiTokenDB, WebhookConfigDB  # noqa: F401

    # Import ALL models so they register with Base.metadata
    from app.modules.items.models import ItemDB  # noqa: F401
    from app.modules.knowledge_base.models import (  # noqa: F401
        DocumentChunkDB,
        KnowledgeBaseDB,
        KnowledgeDocumentDB,
        KnowledgeQueryLogDB,
    )
    from app.modules.subscriptions.models import UserSubscriptionDB  # noqa: F401
    from app.modules.whatsapp.models import WhatsAppDeviceDB, WhatsAppMessageDB  # noqa: F401

    set_engine(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def _session_factory(test_engine):
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(_session_factory):
    """Provide a transactional database session that rolls back after each test."""
    async with _session_factory() as session:
        yield session
        await session.rollback()


async def _truncate_test_database(test_engine):
    """Remove committed test data from every table while respecting foreign keys."""
    async with test_engine.begin() as connection:
        result = await connection.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        table_names = result.scalars().all()
        if not table_names:
            return

        quoted_tables = ", ".join(f'"{name}"' for name in table_names)
        await connection.execute(
            text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture(autouse=True)
async def clean_test_database(test_engine):
    """Give every test a clean DB even when application sessions commit."""
    await _truncate_test_database(test_engine)
    yield
    await _truncate_test_database(test_engine)


# ---------------------------------------------------------------------------
# 5. FastAPI test client with dependency overrides
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(test_engine):
    """Async HTTP client with auth + DB mocked.

    NOTE: We remove BaseHTTPMiddleware (ServerTimingMiddleware) because it runs
    the endpoint in a background task, which conflicts with asyncpg's event loop
    checks in test mode. The middleware is re-added after tests complete.
    """
    from app.core.dependencies import (
        get_current_user,
        get_current_user_id,
        get_current_user_id_flexible,
    )
    with patch("app.config.firebase.initialize_firebase"):
        from app.main import app

    # Remove BaseHTTPMiddleware to avoid event loop conflicts
    app.middleware_stack = None  # Force rebuild

    # Remove ServerTimingMiddleware from the user_middleware list
    original_user_middleware = list(app.user_middleware)
    app.user_middleware = [
        m
        for m in app.user_middleware
        if "ServerTiming" not in getattr(m.cls, "__name__", str(m.cls))
    ]
    app.middleware_stack = None  # Force rebuild on next request

    # Override auth dependencies only - DB uses the patched engine directly
    async def _override_get_current_user():
        return TEST_USER_PAYLOAD

    async def _override_get_current_user_id():
        return TEST_USER_ID

    async def _override_get_current_user_id_flexible():
        return TEST_USER_ID

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_current_user_id] = _override_get_current_user_id
    app.dependency_overrides[get_current_user_id_flexible] = (
        _override_get_current_user_id_flexible
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    # Restore middleware
    app.user_middleware = original_user_middleware
    app.middleware_stack = None


@pytest_asyncio.fixture
async def unauthed_client(test_engine):
    """Async HTTP client WITHOUT auth overrides (for testing 401s).

    No dependency overrides at all - endpoints should return 401/403.
    """
    with patch("app.config.firebase.initialize_firebase"):
        from app.main import app

    # Remove BaseHTTPMiddleware to avoid event loop conflicts
    original_user_middleware = list(app.user_middleware)
    app.user_middleware = [
        m
        for m in app.user_middleware
        if "ServerTiming" not in getattr(m.cls, "__name__", str(m.cls))
    ]
    app.middleware_stack = None

    # Clear any leftover overrides
    app.dependency_overrides.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    app.user_middleware = original_user_middleware
    app.middleware_stack = None


# ---------------------------------------------------------------------------
# 6. Helper fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_uuid():
    """Generate a random UUID string."""
    return str(uuid.uuid4())
