"""add last_gowa_sync_at to whatsapp_devices

Revision ID: 72f79e58219d
Revises: d2e3f4g5h6i7
Create Date: 2026-04-13 18:25:24.019202

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "72f79e58219d"
down_revision: Union[str, Sequence[str], None] = "o4p5q6r7s8t9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "whatsapp_devices",
        sa.Column("last_gowa_sync_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("whatsapp_devices", "last_gowa_sync_at")
