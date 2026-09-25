"""merge_audio_and_widget_heads

Revision ID: 86d343ec6ec1
Revises: 72f79e58219d, d2e3f4g5h6i7
Create Date: 2026-04-27 03:48:55.372520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86d343ec6ec1'
down_revision: Union[str, Sequence[str], None] = ('72f79e58219d', 'd2e3f4g5h6i7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
