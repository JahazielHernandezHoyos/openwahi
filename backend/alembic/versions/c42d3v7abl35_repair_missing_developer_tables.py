"""repair missing developer tables

Revision ID: c42d3v7abl35
Revises: 1127b568ac32
Create Date: 2026-08-27 01:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c42d3v7abl35"
down_revision: Union[str, Sequence[str], None] = "1127b568ac32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        name
        for index in inspector.get_indexes(table_name)
        if (name := index.get("name")) is not None
    }


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    if index_name not in _index_names(table_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    """Restore developer tables skipped by previously stamped databases."""
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())

    if "api_tokens" not in table_names:
        op.create_table(
            "api_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("token_prefix", sa.String(length=16), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "is_active", sa.Boolean(), server_default=sa.true(), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    api_token_indexes = _index_names("api_tokens")
    if "ix_api_tokens_user_id" not in api_token_indexes:
        op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])
    if "ix_api_tokens_token_hash" not in api_token_indexes:
        op.create_index(
            "ix_api_tokens_token_hash", "api_tokens", ["token_hash"], unique=True
        )

    if "webhook_configs" not in table_names:
        op.create_table(
            "webhook_configs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("url", sa.String(length=2048), nullable=False),
            sa.Column("secret", sa.Text(), nullable=True),
            sa.Column(
                "is_active", sa.Boolean(), server_default=sa.true(), nullable=False
            ),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "failure_count", sa.Integer(), server_default="0", nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="webhook_configs_user_id_key"),
        )

    webhook_indexes = _index_names("webhook_configs")
    if "ix_webhook_configs_user_id" not in webhook_indexes:
        op.create_index(
            "ix_webhook_configs_user_id",
            "webhook_configs",
            ["user_id"],
            unique=True,
        )

    _ensure_index(
        "knowledge_bases", "ix_knowledge_bases_is_active", ["is_active"]
    )
    _ensure_index(
        "knowledge_documents", "ix_knowledge_documents_status", ["status"]
    )
    _ensure_index(
        "knowledge_query_logs",
        "ix_knowledge_query_logs_created_at",
        ["created_at"],
    )

    message_constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(
            "whatsapp_messages"
        )
    }
    if "uq_whatsapp_messages_message_device" not in message_constraints:
        op.create_unique_constraint(
            "uq_whatsapp_messages_message_device",
            "whatsapp_messages",
            ["message_id", "device_id"],
        )


def downgrade() -> None:
    """Keep repaired production data intact when downgrading."""
    pass