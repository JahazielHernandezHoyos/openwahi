"""create webhook_tool_configs table for dynamic tools

Revision ID: m1n2o3p4q5r6
Revises: d01a4e8d29ac
Create Date: 2026-02-17 03:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, Sequence[str], None] = "d01a4e8d29ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create webhook_tool_configs table."""

    # Tabla de configuración de herramientas webhook
    op.create_table(
        "webhook_tool_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("webhook_url", sa.String(2048), nullable=False),
        sa.Column("method", sa.String(10), server_default="POST", nullable=False),
        sa.Column("headers", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("input_schema", postgresql.JSON(), nullable=False),
        sa.Column("auth_type", sa.String(20), nullable=True),
        sa.Column("auth_value_encrypted", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), server_default="30", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("requires_confirmation", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Índices
    op.create_index("ix_webhook_tool_configs_user_id", "webhook_tool_configs", ["user_id"])
    op.create_index("ix_webhook_tool_configs_name", "webhook_tool_configs", ["name"])
    op.create_index(
        "ix_webhook_tool_configs_user_name",
        "webhook_tool_configs",
        ["user_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema - drop webhook_tool_configs table."""

    op.drop_index("ix_webhook_tool_configs_user_name", table_name="webhook_tool_configs")
    op.drop_index("ix_webhook_tool_configs_name", table_name="webhook_tool_configs")
    op.drop_index("ix_webhook_tool_configs_user_id", table_name="webhook_tool_configs")
    op.drop_table("webhook_tool_configs")
