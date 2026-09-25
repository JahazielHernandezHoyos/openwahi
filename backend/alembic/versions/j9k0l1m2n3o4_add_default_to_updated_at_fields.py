"""add_default_to_updated_at_fields

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2026-02-02 22:06:54.423194

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j9k0l1m2n3o4"
down_revision: Union[str, Sequence[str], None] = "i8j9k0l1m2n3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add server_default to updated_at columns in knowledge base tables."""

    # Add server_default to knowledge_bases.updated_at
    op.alter_column(
        "knowledge_bases",
        "updated_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    # Add server_default to knowledge_documents.updated_at
    op.alter_column(
        "knowledge_documents",
        "updated_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    # Update existing NULL values to current timestamp
    op.execute(
        "UPDATE knowledge_bases SET updated_at = created_at WHERE updated_at IS NULL"
    )
    op.execute(
        "UPDATE knowledge_documents SET updated_at = created_at WHERE updated_at IS NULL"
    )


def downgrade() -> None:
    """Remove server_default from updated_at columns."""

    # Remove server_default from knowledge_documents.updated_at
    op.alter_column(
        "knowledge_documents",
        "updated_at",
        server_default=None,
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    # Remove server_default from knowledge_bases.updated_at
    op.alter_column(
        "knowledge_bases",
        "updated_at",
        server_default=None,
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
