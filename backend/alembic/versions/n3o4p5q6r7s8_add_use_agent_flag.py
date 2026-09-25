"""add use_agent flag to whatsapp_ai_configs

Revision ID: n3o4p5q6r7s8
Revises: m1n2o3p4q5r6
Create Date: 2026-02-17 03:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n3o4p5q6r7s8"
down_revision: Union[str, Sequence[str], None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add use_agent column to whatsapp_ai_configs."""

    op.add_column(
        "whatsapp_ai_configs",
        sa.Column(
            "use_agent",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Si usar LangGraph agent con herramientas dinámicas",
        ),
    )


def downgrade() -> None:
    """Remove use_agent column."""

    op.drop_column("whatsapp_ai_configs", "use_agent")
