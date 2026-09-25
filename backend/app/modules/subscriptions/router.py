"""Subscriptions API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_id
from app.modules.subscriptions import service
from app.modules.subscriptions.models import SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's plan and device limit."""
    subscription = await service.get_or_create_subscription(db, user_id)
    return service.build_response(subscription)
