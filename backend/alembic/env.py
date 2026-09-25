import asyncio  # <--- Agregado
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine  # <--- Agregado

from alembic import context

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.database import Base
from app.config.settings import settings
from app.modules.ai_assistant.models import (  # noqa: F401
    AIConfigKnowledgeBase,
    AIUsageRecordDB,
    ManagedAIConfigDB,
    ProviderHealthEventDB,
    WebhookToolConfigDB,
    WhatsAppAIConfigDB,
    WhatsAppAIConversationDB,
    WhatsAppAIMessageDB,
)
from app.modules.items.models import ItemDB  # noqa: F401
from app.modules.knowledge_base.models import (  # noqa: F401
    DocumentChunkDB,
    KnowledgeBaseDB,
    KnowledgeDocumentDB,
    KnowledgeQueryLogDB,
)
from app.modules.developer.models import ApiTokenDB, WebhookConfigDB  # noqa: F401
from app.modules.subscriptions.models import UserSubscriptionDB  # noqa: F401
from app.modules.whatsapp.models import WhatsAppDeviceDB, WhatsAppMessageDB  # noqa: F401
from app.modules.widget.models import (  # noqa: F401
    WidgetConversationDB,
    WidgetMessageDB,
    WidgetTokenDB,
)

config = context.config
config.set_main_option("sqlalchemy.url", settings.get_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# --- NUEVA LÓGICA PARA ASYNC ---


def do_run_migrations(connection):
    """Esta función ejecuta las migraciones de forma síncrona."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Modo online: crea un motor asíncrono y usa run_sync."""

    # Creamos el motor asíncrono directamente con la URL de tus settings
    # statement_cache_size=0 keeps migrations compatible with transaction poolers (PgBouncer)
    connectable = create_async_engine(
        settings.get_database_url,
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )

    async with connectable.connect() as connection:
        # El método run_sync es la clave: "engaña" a Alembic para que
        # use la conexión asíncrona como si fuera síncrona.
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# --- CAMBIO EN LA EJECUCIÓN ---

if context.is_offline_mode():
    run_migrations_offline()
else:
    # IMPORTANTE: Usamos asyncio.run para ejecutar la función asíncrona
    asyncio.run(run_migrations_online())
