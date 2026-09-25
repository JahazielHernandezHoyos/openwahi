"""Update instance_port for GOWA v8 multi-device support

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2024-01-28 16:30:00.000000

Changes:
- Update default instance_port from 3001 to 3000 (GOWA v8 uses single instance)
- Update existing devices to use port 3000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database for GOWA v8 multi-device support."""

    # Update default value for instance_port column
    op.alter_column(
        "whatsapp_devices",
        "instance_port",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="3000",
    )

    # Migrate existing devices to use port 3000 (v8 single instance)
    # This is safe because v8 supports multiple devices in one instance
    op.execute(
        """
        UPDATE whatsapp_devices
        SET instance_port = 3000
        WHERE instance_port IN (3001, 3002, 3003)
        """
    )


def downgrade() -> None:
    """Downgrade to previous version."""

    # Restore default value to 3001
    op.alter_column(
        "whatsapp_devices",
        "instance_port",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="3001",
    )

    # Note: We cannot reliably restore the original port assignments
    # as that information is lost. All devices will use port 3001.
    op.execute(
        """
        UPDATE whatsapp_devices
        SET instance_port = 3001
        WHERE instance_port = 3000
        """
    )
