"""refactor kb_ids to relationship table

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2026-02-02 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k0l1m2n3o4p5"
down_revision: Union[str, Sequence[str], None] = "j9k0l1m2n3o4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Refactor knowledge_base_ids from JSONB to proper many-to-many relationship table.
    """

    # 1. Create the new relationship table
    op.create_table(
        "ai_config_knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["ai_config_id"],
            ["whatsapp_ai_configs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "ai_config_id", "knowledge_base_id", name="uq_ai_config_kb"
        ),
    )

    # Create indexes
    op.create_index(
        "ix_ai_config_knowledge_bases_ai_config_id",
        "ai_config_knowledge_bases",
        ["ai_config_id"],
    )
    op.create_index(
        "ix_ai_config_knowledge_bases_knowledge_base_id",
        "ai_config_knowledge_bases",
        ["knowledge_base_id"],
    )

    # 2. Migrate existing data from JSONB to relationship table
    # This SQL extracts each UUID from the JSONB array and inserts it as a relationship
    op.execute(
        """
        INSERT INTO ai_config_knowledge_bases (id, ai_config_id, knowledge_base_id, created_at)
        SELECT
            gen_random_uuid() as id,
            wac.id as ai_config_id,
            (kb_id::text)::uuid as knowledge_base_id,
            NOW() as created_at
        FROM whatsapp_ai_configs wac,
             jsonb_array_elements_text(wac.knowledge_base_ids) as kb_id
        WHERE jsonb_array_length(wac.knowledge_base_ids) > 0
        ON CONFLICT DO NOTHING;
        """
    )

    # 3. Drop the old JSONB column
    op.drop_column("whatsapp_ai_configs", "knowledge_base_ids")


def downgrade() -> None:
    """
    Revert back to JSONB column (with data loss of relationship timestamps).
    """

    # 1. Add back the JSONB column
    op.add_column(
        "whatsapp_ai_configs",
        sa.Column(
            "knowledge_base_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )

    # 2. Migrate data back from relationship table to JSONB
    op.execute(
        """
        UPDATE whatsapp_ai_configs wac
        SET knowledge_base_ids = COALESCE(
            (
                SELECT jsonb_agg(kb.knowledge_base_id::text)
                FROM ai_config_knowledge_bases kb
                WHERE kb.ai_config_id = wac.id
            ),
            '[]'::jsonb
        );
        """
    )

    # 3. Drop the relationship table
    op.drop_index(
        "ix_ai_config_knowledge_bases_knowledge_base_id",
        table_name="ai_config_knowledge_bases",
    )
    op.drop_index(
        "ix_ai_config_knowledge_bases_ai_config_id",
        table_name="ai_config_knowledge_bases",
    )
    op.drop_table("ai_config_knowledge_bases")
