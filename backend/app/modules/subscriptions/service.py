"""Subscription service layer."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscriptions.models import (
    PLAN_DEVICE_LIMITS,
    Plan,
    SubscriptionResponse,
    UserSubscriptionDB,
)

logger = logging.getLogger(__name__)


async def get_or_create_subscription(db: AsyncSession, user_id: str) -> UserSubscriptionDB:
    """Get the user's subscription or create a free one if it doesn't exist."""
    result = await db.execute(
        select(UserSubscriptionDB).where(UserSubscriptionDB.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        subscription = UserSubscriptionDB(
            user_id=user_id,
            plan=Plan.free,
            status="active",
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        logger.info(f"Created free subscription for user {user_id}")

    return subscription


async def get_device_limit(db: AsyncSession, user_id: str) -> int:
    """Return the maximum number of WhatsApp devices allowed for this user."""
    subscription = await get_or_create_subscription(db, user_id)
    return PLAN_DEVICE_LIMITS.get(subscription.plan, 1)


def build_response(subscription: UserSubscriptionDB) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        plan=subscription.plan,
        status=subscription.status,
        device_limit=PLAN_DEVICE_LIMITS.get(subscription.plan, 1),
        created_at=subscription.created_at,
    )
