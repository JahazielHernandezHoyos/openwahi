from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config.settings import settings

# Lazy engine initialization to avoid event loop conflicts in tests.
# The engine and session factory are created on first use, not at import time.
_engine = None
_async_session_local = None

# Create declarative base for models
Base = declarative_base()


def get_engine():
    """Get or create the async engine (lazy initialization)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.get_database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
            },
        )
    return _engine


def get_session_factory():
    """Get or create the async session factory (lazy initialization)."""
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_local


def set_engine(engine):
    """Override the engine (used by tests)."""
    global _engine, _async_session_local
    _engine = engine
    _async_session_local = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Backward compatibility: expose as module-level properties
# These are accessed by some code that imports `engine` or `AsyncSessionLocal` directly.
class _EngineProxy:
    """Proxy that lazily initializes the engine on first attribute access."""

    def __getattr__(self, name):
        return getattr(get_engine(), name)

    def __repr__(self):
        return repr(get_engine())


class _SessionFactoryProxy:
    """Proxy that lazily initializes the session factory on first call."""

    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(get_session_factory(), name)


engine = _EngineProxy()
AsyncSessionLocal = _SessionFactoryProxy()


# Dependency for FastAPI
async def get_db():
    """
    Database session dependency for FastAPI.
    Properly handles rollback on exceptions to prevent
    'current transaction is aborted' errors.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
