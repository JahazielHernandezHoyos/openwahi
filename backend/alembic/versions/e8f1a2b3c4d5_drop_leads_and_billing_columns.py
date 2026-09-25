"""drop leads table and external billing columns

Revision ID: e8f1a2b3c4d5
Revises: f3a9c1d7e5b2
Create Date: 2026-09-24 12:00:00.000000

Removes the waitlist ``leads`` table and the ``user_subscriptions`` columns that
were only populated by the removed hosted-billing integration. Plans remain
operator-assigned from the admin panel.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "f3a9c1d7e5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_table("leads")

    op.drop_index(
        "ix_user_subscriptions_ls_subscription_id", table_name="user_subscriptions"
    )
    op.drop_column("user_subscriptions", "ls_subscription_id")
    op.drop_column("user_subscriptions", "ls_customer_id")
    op.drop_column("user_subscriptions", "ls_variant_id")
    op.drop_column("user_subscriptions", "renews_at")
    op.drop_column("user_subscriptions", "current_period_end")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "user_subscriptions",
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_subscriptions",
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_subscriptions",
        sa.Column("ls_variant_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_subscriptions",
        sa.Column("ls_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_subscriptions",
        sa.Column("ls_subscription_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_user_subscriptions_ls_subscription_id",
        "user_subscriptions",
        ["ls_subscription_id"],
        unique=True,
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_email", "leads", ["email"], unique=True)
