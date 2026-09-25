"""preserve data on device unlink - change CASCADE to SET NULL for messages and ai_configs

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
Create Date: 2026-03-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o4p5q6r7s8t9"
down_revision: Union[str, None] = "d1726db3964c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change FK ondelete rules so that unlinking a WhatsApp device does NOT
    delete its associated messages, AI assistant config, or knowledge bases.

    Before:
      - whatsapp_messages.device_id        → ON DELETE CASCADE  (all chats wiped)
      - whatsapp_ai_configs.device_id      → ON DELETE CASCADE  (AI config wiped)

    After:
      - whatsapp_messages.device_id        → ON DELETE SET NULL (chats preserved, device_id nulled)
      - whatsapp_ai_configs.device_id      → ON DELETE SET NULL (config preserved, device_id nulled)

    knowledge_bases.device_id already uses ON DELETE SET NULL — no change needed.
    ai_config_knowledge_bases.ai_config_id keeps CASCADE (join table, not real data).
    """

    # --- whatsapp_messages.device_id: CASCADE → SET NULL ---
    # Also make the column nullable so SET NULL can work.
    op.drop_constraint(
        "whatsapp_messages_device_id_fkey",
        "whatsapp_messages",
        type_="foreignkey",
    )
    op.alter_column("whatsapp_messages", "device_id", nullable=True)
    op.create_foreign_key(
        "whatsapp_messages_device_id_fkey",
        "whatsapp_messages",
        "whatsapp_devices",
        ["device_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- whatsapp_ai_configs.device_id: CASCADE → SET NULL ---
    op.drop_constraint(
        "whatsapp_ai_configs_device_id_fkey",
        "whatsapp_ai_configs",
        type_="foreignkey",
    )
    op.alter_column("whatsapp_ai_configs", "device_id", nullable=True)
    op.create_foreign_key(
        "whatsapp_ai_configs_device_id_fkey",
        "whatsapp_ai_configs",
        "whatsapp_devices",
        ["device_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert to original CASCADE behavior."""

    # --- whatsapp_ai_configs.device_id: SET NULL → CASCADE ---
    op.drop_constraint(
        "whatsapp_ai_configs_device_id_fkey",
        "whatsapp_ai_configs",
        type_="foreignkey",
    )
    op.alter_column("whatsapp_ai_configs", "device_id", nullable=False)
    op.create_foreign_key(
        "whatsapp_ai_configs_device_id_fkey",
        "whatsapp_ai_configs",
        "whatsapp_devices",
        ["device_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- whatsapp_messages.device_id: SET NULL → CASCADE ---
    op.drop_constraint(
        "whatsapp_messages_device_id_fkey",
        "whatsapp_messages",
        type_="foreignkey",
    )
    op.alter_column("whatsapp_messages", "device_id", nullable=False)
    op.create_foreign_key(
        "whatsapp_messages_device_id_fkey",
        "whatsapp_messages",
        "whatsapp_devices",
        ["device_id"],
        ["id"],
        ondelete="CASCADE",
    )
