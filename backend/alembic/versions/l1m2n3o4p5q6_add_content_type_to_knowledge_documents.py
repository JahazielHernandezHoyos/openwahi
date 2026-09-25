"""add content_type to knowledge_documents

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2026-02-02 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l1m2n3o4p5q6'
down_revision: Union[str, None] = 'k0l1m2n3o4p5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add content_type column to knowledge_documents table
    op.add_column('knowledge_documents', sa.Column('content_type', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove content_type column
    op.drop_column('knowledge_documents', 'content_type')
