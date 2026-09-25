"""fix token_prefix column length

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2025-01-29 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g6h7i8j9k0l1"
down_revision: Union[str, Sequence[str], None] = "f5g6h7i8j9k0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - fix token_prefix length."""
    op.alter_column(
        "api_tokens",
        "token_prefix",
        existing_type=sa.String(8),
        type_=sa.String(16),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema - revert token_prefix length."""
    op.alter_column(
        "api_tokens",
        "token_prefix",
        existing_type=sa.String(16),
        type_=sa.String(8),
        existing_nullable=False,
    )
