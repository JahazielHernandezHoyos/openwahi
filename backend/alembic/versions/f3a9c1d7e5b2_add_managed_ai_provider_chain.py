"""add managed AI provider chain

Revision ID: f3a9c1d7e5b2
Revises: c42d3v7abl35
Create Date: 2026-09-06 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f3a9c1d7e5b2"
down_revision: Union[str, Sequence[str], None] = "c42d3v7abl35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "managed_ai_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("requires_tools", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_healthy", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_probe_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_probe_latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position", name="uq_managed_ai_config_position"),
    )
    op.create_table(
        "provider_health_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managed_ai_config.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_health_events_entry_id",
        "provider_health_events",
        ["entry_id"],
    )
    op.create_index(
        "ix_provider_health_events_event_type",
        "provider_health_events",
        ["event_type"],
    )
    op.create_index(
        "ix_provider_health_events_created_at",
        "provider_health_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_health_events_created_at", table_name="provider_health_events"
    )
    op.drop_index(
        "ix_provider_health_events_event_type", table_name="provider_health_events"
    )
    op.drop_index(
        "ix_provider_health_events_entry_id", table_name="provider_health_events"
    )
    op.drop_table("provider_health_events")
    op.drop_table("managed_ai_config")
