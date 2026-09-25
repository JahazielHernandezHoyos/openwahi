"""add user_subscriptions table

Revision ID: 1e1c821ff0cb
Revises: o4p5q6r7s8t9
Create Date: 2026-03-08 12:16:32.283703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1e1c821ff0cb'
down_revision: Union[str, Sequence[str], None] = 'o4p5q6r7s8t9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Idempotent: some environments already have this enum/table from a
    # previous (superseded) revision. Skip creation if present.
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan') THEN "
        "CREATE TYPE plan AS ENUM ('free', 'pro', 'enterprise'); "
        "END IF; END $$;"
    )

    if not inspector.has_table('user_subscriptions'):
        op.create_table(
            'user_subscriptions',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.String(length=128), nullable=False),
            sa.Column(
                'plan',
                postgresql.ENUM('free', 'pro', 'enterprise', name='plan', create_type=False),
                nullable=False,
            ),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
            sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
            sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    existing_indexes = {ix['name'] for ix in inspector.get_indexes('user_subscriptions')} if inspector.has_table('user_subscriptions') else set()
    if op.f('ix_user_subscriptions_user_id') not in existing_indexes:
        op.create_index(
            op.f('ix_user_subscriptions_user_id'),
            'user_subscriptions',
            ['user_id'],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_user_subscriptions_user_id'), table_name='user_subscriptions')
    op.drop_table('user_subscriptions')
    op.execute("DROP TYPE IF EXISTS plan")
