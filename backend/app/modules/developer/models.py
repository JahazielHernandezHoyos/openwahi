"""Models for API tokens and webhook configurations."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base

# SQLAlchemy Models


class ApiTokenDB(Base):
    """Database model for API tokens."""

    __tablename__ = "api_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    token_prefix = Column(String(16), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WebhookConfigDB(Base):
    """Database model for webhook configurations."""

    __tablename__ = "webhook_configs"
    __table_args__ = (UniqueConstraint("user_id", name="webhook_configs_user_id_key"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, unique=True, index=True)
    url = Column(String(2048), nullable=False)
    secret = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), nullable=True)


# Pydantic Schemas


class ApiTokenCreate(BaseModel):
    """Schema for creating an API token."""

    name: str = Field(..., min_length=1, max_length=100, description="Token name")


class ApiTokenResponse(BaseModel):
    """Schema for API token response (without the actual token)."""

    id: str
    name: str
    token_prefix: str
    last_used_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenCreatedResponse(BaseModel):
    """Schema for newly created API token (includes full token - shown only once)."""

    id: str
    name: str
    token: str = Field(
        ..., description="Full API token - save this, it won't be shown again"
    )
    token_prefix: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenListResponse(BaseModel):
    """Schema for list of API tokens."""

    tokens: list[ApiTokenResponse]
    total: int


class WebhookConfigCreate(BaseModel):
    """Schema for creating/updating webhook configuration."""

    url: str = Field(..., min_length=1, max_length=2048, description="Webhook URL")
    secret: Optional[str] = Field(None, description="Optional secret for HMAC signing")
    is_active: bool = Field(True, description="Whether webhook is active")


class WebhookConfigResponse(BaseModel):
    """Schema for webhook configuration response."""

    id: str
    url: str
    has_secret: bool = Field(..., description="Whether a secret is configured")
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    failure_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WebhookTestRequest(BaseModel):
    """Schema for testing webhook."""

    pass  # No parameters needed, uses configured webhook


class WebhookTestResponse(BaseModel):
    """Schema for webhook test result."""

    success: bool
    status_code: Optional[int] = None
    message: str
    response_time_ms: Optional[int] = None
