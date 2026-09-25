"""
Widget module models - Pydantic schemas and SQLAlchemy models.

Manages embeddable chat widget tokens and conversations.
"""

import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


# ==================== SQLAlchemy Models ====================


def generate_widget_token() -> str:
    """Generate a unique widget token with 'wgt_' prefix."""
    return "wgt_" + secrets.token_urlsafe(32)


class WidgetTokenDB(Base):
    """
    Widget token — issued to a user so they can embed a chat widget
    on their own website. Each token is linked to an AI config.
    """

    __tablename__ = "widget_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    ai_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_ai_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The actual token value used in the script tag
    token = Column(
        String(64), nullable=False, unique=True, index=True, default=generate_widget_token
    )

    # Human-readable label (e.g. "Support widget - my-shop.com")
    name = Column(String(100), nullable=False)

    # Optional: restrict which domains may use this token (comma-separated)
    # If NULL, all origins are allowed
    allowed_origins = Column(Text, nullable=True)

    # Widget appearance colors — hex strings (e.g. "#2563eb").
    # If NULL the widget uses its own defaults.
    primary_color = Column(String(20), nullable=True)
    secondary_color = Column(String(20), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    conversations = relationship(
        "WidgetConversationDB",
        back_populates="widget_token",
        cascade="all, delete-orphan",
    )


class WidgetConversationDB(Base):
    """
    Conversation between a visitor and the widget AI.

    Visitor identity is provided by the browser (localStorage UUID).
    """

    __tablename__ = "widget_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    widget_token_id = Column(
        UUID(as_uuid=True),
        ForeignKey("widget_tokens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Visitor identifier from browser localStorage (openwahi_visitor_id)
    visitor_id = Column(String(128), nullable=False, index=True)

    message_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    widget_token = relationship("WidgetTokenDB", back_populates="conversations")
    messages = relationship(
        "WidgetMessageDB",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="WidgetMessageDB.created_at",
    )


class WidgetMessageDB(Base):
    """Individual message in a widget conversation."""

    __tablename__ = "widget_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("widget_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # AI metadata (assistant messages only)
    provider = Column(String(20), nullable=True)
    model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("WidgetConversationDB", back_populates="messages")


# ==================== Pydantic Schemas ====================


class WidgetTokenCreate(BaseModel):
    """Schema for creating a widget token."""

    name: str = Field(..., min_length=1, max_length=100)
    ai_config_id: uuid.UUID
    allowed_origins: Optional[str] = None  # Comma-separated list of allowed origins
    primary_color: Optional[str] = Field(None, max_length=20, description="Hex color, e.g. #2563eb")
    secondary_color: Optional[str] = Field(
        None, max_length=20, description="Hex color, e.g. #1e40af"
    )


class WidgetTokenResponse(BaseModel):
    """Schema for widget token response."""

    id: uuid.UUID
    user_id: str
    ai_config_id: uuid.UUID
    token: str
    name: str
    allowed_origins: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class WidgetChatRequest(BaseModel):
    """Schema for sending a message via the public widget endpoint."""

    visitor_id: str = Field(
        ..., min_length=1, max_length=128, description="UUID generated in browser (localStorage)"
    )
    message: str = Field(..., min_length=1, max_length=4000)
    widget_token: str = Field(..., description="Token from data-widget-token attribute")


class WidgetChatResponse(BaseModel):
    """Schema for widget chat response."""

    reply: str
    visitor_id: str
    conversation_id: uuid.UUID


class WidgetMessageResponse(BaseModel):
    """Schema for a single message in widget history."""

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class WidgetHistoryResponse(BaseModel):
    """Schema for widget conversation history."""

    conversation_id: uuid.UUID
    visitor_id: str
    message_count: int
    messages: List[WidgetMessageResponse]

    class Config:
        from_attributes = True


class WidgetConfigResponse(BaseModel):
    """
    Public configuration for a widget token.

    Returned by GET /widget/config and consumed by widget.js at init time.
    Contains only the info safe to expose publicly (no user IDs, no secrets).
    """

    token: str
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    title: Optional[str] = None  # Reserved for future per-token title config
