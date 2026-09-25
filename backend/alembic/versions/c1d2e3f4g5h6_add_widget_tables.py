"""add widget tables and ai config standalone fields

Revision ID: c1d2e3f4g5h6
Revises: b371684c3251
Create Date: 2026-03-08 00:00:00.000000

Changes:
- whatsapp_ai_configs: phone_number nullable (was NOT NULL)
- whatsapp_ai_configs: add name column (VARCHAR 100, nullable)
- Create widget_tokens table
- Create widget_conversations table
- Create widget_messages table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, Sequence[str], None] = "b371684c3251"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. whatsapp_ai_configs: make phone_number nullable ──────────────────
    op.alter_column(
        "whatsapp_ai_configs",
        "phone_number",
        existing_type=sa.String(50),
        nullable=True,
    )

    # ── 2. whatsapp_ai_configs: add name column ──────────────────────────────
    op.add_column(
        "whatsapp_ai_configs",
        sa.Column("name", sa.String(100), nullable=True),
    )

    # ── 3. widget_tokens ─────────────────────────────────────────────────────
    op.create_table(
        "widget_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column(
            "ai_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_ai_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("allowed_origins", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_widget_tokens_user_id", "widget_tokens", ["user_id"])
    op.create_index("ix_widget_tokens_ai_config_id", "widget_tokens", ["ai_config_id"])
    op.create_index("ix_widget_tokens_token", "widget_tokens", ["token"], unique=True)

    # ── 4. widget_conversations ───────────────────────────────────────────────
    op.create_table(
        "widget_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "widget_token_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("widget_tokens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("visitor_id", sa.String(128), nullable=False),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_widget_conversations_widget_token_id",
        "widget_conversations",
        ["widget_token_id"],
    )
    op.create_index(
        "ix_widget_conversations_visitor_id",
        "widget_conversations",
        ["visitor_id"],
    )

    # ── 5. widget_messages ────────────────────────────────────────────────────
    op.create_table(
        "widget_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("widget_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("provider", sa.String(20), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_widget_messages_conversation_id",
        "widget_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    # Drop widget tables in reverse order
    op.drop_index("ix_widget_messages_conversation_id", table_name="widget_messages")
    op.drop_table("widget_messages")

    op.drop_index("ix_widget_conversations_visitor_id", table_name="widget_conversations")
    op.drop_index("ix_widget_conversations_widget_token_id", table_name="widget_conversations")
    op.drop_table("widget_conversations")

    op.drop_index("ix_widget_tokens_token", table_name="widget_tokens")
    op.drop_index("ix_widget_tokens_ai_config_id", table_name="widget_tokens")
    op.drop_index("ix_widget_tokens_user_id", table_name="widget_tokens")
    op.drop_table("widget_tokens")

    # Remove name column from whatsapp_ai_configs
    op.drop_column("whatsapp_ai_configs", "name")

    # Revert phone_number to NOT NULL — set empty strings first to avoid failures
    op.execute("UPDATE whatsapp_ai_configs SET phone_number = '' WHERE phone_number IS NULL")
    op.alter_column(
        "whatsapp_ai_configs",
        "phone_number",
        existing_type=sa.String(50),
        nullable=False,
    )
