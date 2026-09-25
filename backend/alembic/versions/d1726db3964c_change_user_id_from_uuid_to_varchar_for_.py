"""change user_id from uuid to varchar for firebase compatibility

Revision ID: d1726db3964c
Revises: n3o4p5q6r7s8
Create Date: 2026-02-24 21:08:36.352105

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d1726db3964c"
down_revision: Union[str, Sequence[str], None] = "n3o4p5q6r7s8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change all user_id columns from UUID to VARCHAR(128) to support Firebase UIDs.
    Firebase UIDs are alphanumeric strings (e.g. "abc123XYZ"), not UUIDs.

    Uses to_regclass() instead of ::regclass to avoid UndefinedTableError when
    the table doesn't exist — to_regclass() returns NULL rather than throwing.
    """
    tables_with_user_id = [
        "whatsapp_devices",
        "whatsapp_ai_configs",
        "knowledge_bases",
        "knowledge_query_logs",
        "api_tokens",
        "webhook_configs",
        "webhook_tool_configs",
    ]

    # Drop the unique constraint on webhook_configs BEFORE the loop alters that column.
    # The constraint was created by f5g6h7i8j9k0 as webhook_configs_user_id_key.
    # Use to_regclass() so this is a no-op if the table or constraint doesn't exist.
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('public.webhook_configs') IS NOT NULL AND EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = to_regclass('public.webhook_configs')
                AND conname = 'webhook_configs_user_id_key'
            ) THEN
                ALTER TABLE webhook_configs DROP CONSTRAINT webhook_configs_user_id_key;
            END IF;
        END$$;
    """)

    for table in tables_with_user_id:
        # Drop existing index on user_id if it exists
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = '{table}' AND indexname = 'ix_{table}_user_id'
                ) THEN
                    EXECUTE 'DROP INDEX ix_{table}_user_id';
                END IF;
            END$$;
        """)

        # Change column type UUID -> VARCHAR(128), only if the column is not already varchar.
        # Uses to_regclass() to skip silently if the table doesn't exist.
        op.execute(f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table}') IS NOT NULL AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = '{table}'
                      AND column_name = 'user_id'
                      AND data_type = 'uuid'
                ) THEN
                    ALTER TABLE {table}
                    ALTER COLUMN user_id TYPE VARCHAR(128)
                    USING user_id::text;
                END IF;
            END$$;
        """)

        # Recreate index (only if it doesn't already exist)
        op.execute(f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table}') IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = '{table}' AND indexname = 'ix_{table}_user_id'
                ) AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = '{table}'
                      AND column_name = 'user_id'
                ) THEN
                    EXECUTE 'CREATE INDEX ix_{table}_user_id ON {table} (user_id)';
                END IF;
            END$$;
        """)

    # Recreate unique constraint on webhook_configs.user_id
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('public.webhook_configs') IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = to_regclass('public.webhook_configs')
                AND conname = 'webhook_configs_user_id_key'
            ) THEN
                ALTER TABLE webhook_configs
                ADD CONSTRAINT webhook_configs_user_id_key UNIQUE (user_id);
            END IF;
        END$$;
    """)

    # Fix the use_agent column comment detected by autogenerate
    op.alter_column(
        "whatsapp_ai_configs",
        "use_agent",
        existing_type=sa.BOOLEAN(),
        comment=None,
        existing_comment="Si usar LangGraph agent con herramientas dinámicas",
        existing_nullable=False,
        existing_server_default=sa.text("false"),
    )


def downgrade() -> None:
    """Revert user_id columns back to UUID (only works if all values are valid UUIDs)."""
    tables_with_user_id = [
        "whatsapp_devices",
        "whatsapp_ai_configs",
        "knowledge_bases",
        "knowledge_query_logs",
        "api_tokens",
        "webhook_configs",
        "webhook_tool_configs",
    ]

    for table in tables_with_user_id:
        op.execute(f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table}') IS NOT NULL AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = '{table}'
                      AND column_name = 'user_id'
                      AND data_type = 'character varying'
                ) THEN
                    ALTER TABLE {table}
                    ALTER COLUMN user_id TYPE UUID
                    USING user_id::uuid;
                END IF;
            END$$;
        """)

    op.alter_column(
        "whatsapp_ai_configs",
        "use_agent",
        existing_type=sa.BOOLEAN(),
        comment="Si usar LangGraph agent con herramientas dinámicas",
        existing_nullable=False,
        existing_server_default=sa.text("false"),
    )
