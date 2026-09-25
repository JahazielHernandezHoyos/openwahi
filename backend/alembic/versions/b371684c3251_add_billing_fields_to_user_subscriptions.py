"""add external billing fields to user_subscriptions

Revision ID: b371684c3251
Revises: 1e1c821ff0cb
Create Date: 2026-03-08 13:26:12.054210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b371684c3251'
down_revision: Union[str, Sequence[str], None] = '1e1c821ff0cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_subscriptions', sa.Column('ls_subscription_id', sa.String(255), nullable=True))
    op.add_column('user_subscriptions', sa.Column('ls_customer_id', sa.String(255), nullable=True))
    op.add_column('user_subscriptions', sa.Column('ls_variant_id', sa.String(255), nullable=True))
    op.add_column('user_subscriptions', sa.Column('renews_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_user_subscriptions_ls_subscription_id', 'user_subscriptions', ['ls_subscription_id'], unique=True)
    op.drop_column('user_subscriptions', 'stripe_customer_id')
    op.drop_column('user_subscriptions', 'stripe_subscription_id')


def downgrade() -> None:
    op.add_column('user_subscriptions', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))
    op.add_column('user_subscriptions', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.drop_index('ix_user_subscriptions_ls_subscription_id', table_name='user_subscriptions')
    op.drop_column('user_subscriptions', 'renews_at')
    op.drop_column('user_subscriptions', 'ls_variant_id')
    op.drop_column('user_subscriptions', 'ls_customer_id')
    op.drop_column('user_subscriptions', 'ls_subscription_id')
