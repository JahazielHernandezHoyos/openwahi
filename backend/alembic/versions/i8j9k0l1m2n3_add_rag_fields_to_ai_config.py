"""add RAG fields to AI config

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2025-01-31 11:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i8j9k0l1m2n3"
down_revision: Union[str, Sequence[str], None] = "h7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add RAG fields to whatsapp_ai_configs."""

    # Add RAG-related columns to whatsapp_ai_configs
    op.add_column(
        "whatsapp_ai_configs",
        sa.Column(
            "use_knowledge_base",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )

    op.add_column(
        "whatsapp_ai_configs",
        sa.Column(
            "knowledge_base_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )

    op.add_column(
        "whatsapp_ai_configs",
        sa.Column(
            "rag_top_k",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
    )

    op.add_column(
        "whatsapp_ai_configs",
        sa.Column(
            "rag_min_score",
            sa.Float(),
            server_default="0.75",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema - remove RAG fields from whatsapp_ai_configs."""

    op.drop_column("whatsapp_ai_configs", "rag_min_score")
    op.drop_column("whatsapp_ai_configs", "rag_top_k")
    op.drop_column("whatsapp_ai_configs", "knowledge_base_ids")
    op.drop_column("whatsapp_ai_configs", "use_knowledge_base")
