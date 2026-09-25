"""create ai assistant tables

Revision ID: e4f5g6h7i8j9
Revises: c3d4e5f6g7h8
Create Date: 2025-01-29 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f5g6h7i8j9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create AI assistant tables."""

    # Tabla de configuración de IA por dispositivo/número
    op.create_table(
        "whatsapp_ai_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=False),
        # AI Configuration
        sa.Column("provider", sa.String(20), server_default="groq", nullable=False),
        sa.Column(
            "model",
            sa.String(100),
            server_default="llama-3.3-70b-versatile",
            nullable=False,
        ),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        # Bot Settings
        sa.Column("is_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("max_tokens", sa.Integer(), server_default="1000", nullable=False),
        # Advanced Settings
        sa.Column("use_memory", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("memory_window", sa.Integer(), server_default="10", nullable=False),
        sa.Column(
            "auto_enhance_prompt", sa.Boolean(), server_default="true", nullable=False
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["device_id"], ["whatsapp_devices.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_whatsapp_ai_configs_device_id", "whatsapp_ai_configs", ["device_id"]
    )
    op.create_index(
        "ix_whatsapp_ai_configs_user_id", "whatsapp_ai_configs", ["user_id"]
    )
    op.create_index(
        "ix_whatsapp_ai_configs_phone_number", "whatsapp_ai_configs", ["phone_number"]
    )

    # Tabla de conversaciones con IA
    op.create_table(
        "whatsapp_ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_phone", sa.String(50), nullable=False),
        # Metadata
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["whatsapp_ai_configs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_whatsapp_ai_conversations_config_id",
        "whatsapp_ai_conversations",
        ["config_id"],
    )
    op.create_index(
        "ix_whatsapp_ai_conversations_from_phone",
        "whatsapp_ai_conversations",
        ["from_phone"],
    )

    # Tabla de mensajes individuales en conversaciones de IA
    op.create_table(
        "whatsapp_ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("whatsapp_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Message Content
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # AI Metadata
        sa.Column("provider", sa.String(20), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        # Timestamp
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["whatsapp_ai_conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["whatsapp_message_id"], ["whatsapp_messages.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_whatsapp_ai_messages_conversation_id",
        "whatsapp_ai_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    """Downgrade schema - drop AI assistant tables."""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index(
        "ix_whatsapp_ai_messages_conversation_id", table_name="whatsapp_ai_messages"
    )
    op.drop_table("whatsapp_ai_messages")

    op.drop_index(
        "ix_whatsapp_ai_conversations_from_phone",
        table_name="whatsapp_ai_conversations",
    )
    op.drop_index(
        "ix_whatsapp_ai_conversations_config_id", table_name="whatsapp_ai_conversations"
    )
    op.drop_table("whatsapp_ai_conversations")

    op.drop_index(
        "ix_whatsapp_ai_configs_phone_number", table_name="whatsapp_ai_configs"
    )
    op.drop_index("ix_whatsapp_ai_configs_user_id", table_name="whatsapp_ai_configs")
    op.drop_index("ix_whatsapp_ai_configs_device_id", table_name="whatsapp_ai_configs")
    op.drop_table("whatsapp_ai_configs")
