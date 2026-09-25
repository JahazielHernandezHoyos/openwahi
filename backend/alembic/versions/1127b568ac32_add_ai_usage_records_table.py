"""add_ai_usage_records_table

Revision ID: 1127b568ac32
Revises: 86d343ec6ec1
Create Date: 2026-04-27 17:11:56.533978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1127b568ac32'
down_revision: Union[str, Sequence[str], None] = '86d343ec6ec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False),
        sa.Column("tokens_output", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("is_managed", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["whatsapp_ai_configs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["whatsapp_ai_conversations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_usage_records_config_id"), "ai_usage_records", ["config_id"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_conversation_id"), "ai_usage_records", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_created_at"), "ai_usage_records", ["created_at"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_user_id"), "ai_usage_records", ["user_id"], unique=False)
    op.create_index("ix_ai_usage_user_created", "ai_usage_records", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_ai_usage_user_created", table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_user_id"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_created_at"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_conversation_id"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_config_id"), table_name="ai_usage_records")
    op.drop_table("ai_usage_records")
