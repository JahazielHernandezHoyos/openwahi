"""Add instance_port column to whatsapp_devices.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2024-01-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add instance_port column with default value 3001
    op.add_column(
        'whatsapp_devices',
        sa.Column('instance_port', sa.Integer(), nullable=False, server_default='3001')
    )


def downgrade() -> None:
    op.drop_column('whatsapp_devices', 'instance_port')
