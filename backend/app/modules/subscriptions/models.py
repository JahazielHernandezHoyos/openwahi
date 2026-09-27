"""Subscription models for operator-assigned plans."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.config.database import Base


class Plan(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


PLAN_DEVICE_LIMITS: dict[Plan, int] = {
    Plan.free: 1,
    Plan.pro: 10,
    Plan.enterprise: 100,
}


class UserSubscriptionDB(Base):
    """User subscription database model."""

    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, unique=True, index=True)
    plan = Column(SQLEnum(Plan), nullable=False, default=Plan.free)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ==================== Pydantic Schemas ====================


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    plan: Plan
    status: str
    device_limit: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
