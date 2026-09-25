"""add primary_color and secondary_color to widget_tokens

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-03-09 00:00:00.000000

Changes:
- widget_tokens: add primary_color column (VARCHAR 20, nullable)
- widget_tokens: add secondary_color column (VARCHAR 20, nullable)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4g5h6i7"
down_revision: Union[str, None] = "c1d2e3f4g5h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "widget_tokens",
        sa.Column("primary_color", sa.String(20), nullable=True),
    )
    op.add_column(
        "widget_tokens",
        sa.Column("secondary_color", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("widget_tokens", "secondary_color")
    op.drop_column("widget_tokens", "primary_color")
