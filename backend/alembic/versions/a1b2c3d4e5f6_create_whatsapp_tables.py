"""create whatsapp tables

Revision ID: a1b2c3d4e5f6
Revises: d6281dc987b5
Create Date: 2026-01-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd6281dc987b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Tabla de dispositivos WhatsApp vinculados
    op.create_table('whatsapp_devices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id')
    )
    op.create_index('ix_whatsapp_devices_user_id', 'whatsapp_devices', ['user_id'])

    # Tabla de mensajes WhatsApp
    op.create_table('whatsapp_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.UUID(), nullable=True),
        sa.Column('message_id', sa.String(255), nullable=False),
        sa.Column('from_phone', sa.String(50), nullable=False),
        sa.Column('to_phone', sa.String(50), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('message_type', sa.String(20), server_default='text', nullable=False),
        sa.Column('is_from_me', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', sa.String(20), server_default='received', nullable=False),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['device_id'], ['whatsapp_devices.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('message_id', 'device_id', name='uq_whatsapp_messages_message_device')
    )
    op.create_index('ix_whatsapp_messages_device_id', 'whatsapp_messages', ['device_id'])
    op.create_index('ix_whatsapp_messages_timestamp', 'whatsapp_messages', ['timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_whatsapp_messages_timestamp', table_name='whatsapp_messages')
    op.drop_index('ix_whatsapp_messages_device_id', table_name='whatsapp_messages')
    op.drop_table('whatsapp_messages')
    op.drop_index('ix_whatsapp_devices_user_id', table_name='whatsapp_devices')
    op.drop_table('whatsapp_devices')
