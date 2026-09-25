"""WhatsApp models for database and API schemas."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base

# ==================== SQLAlchemy Models ====================


class WhatsAppDeviceDB(Base):
    """WhatsApp device/session database model."""

    __tablename__ = "whatsapp_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    device_id = Column(
        String(255), nullable=False, unique=True
    )  # GOWA v8 device ID (e.g., 628123456789@s.whatsapp.net)
    instance_port = Column(
        Integer, nullable=False, default=3000
    )  # GOWA instance port (v8 uses single instance on 3000)
    phone = Column(String(20), nullable=True)
    name = Column(String(255), nullable=True)
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, connected, disconnected
    connected_at = Column(DateTime(timezone=True), nullable=True)
    last_gowa_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship(
        "WhatsAppMessageDB", back_populates="device", cascade="save-update, merge"
    )


class WhatsAppMessageDB(Base):
    """WhatsApp message database model."""

    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        UniqueConstraint(
            "message_id", "device_id", name="uq_whatsapp_messages_message_device"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id = Column(String(255), nullable=False)  # WhatsApp message ID
    from_phone = Column(String(50), nullable=False)
    to_phone = Column(String(50), nullable=False)
    body = Column(Text, nullable=True)
    message_type = Column(
        String(20), default="text", nullable=False
    )  # text, image, document, etc.
    is_from_me = Column(Boolean, default=False, nullable=False)
    status = Column(
        String(20), default="received", nullable=False
    )  # received, sent, delivered, read
    media_url = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("WhatsAppDeviceDB", back_populates="messages")


# ==================== Pydantic Schemas ====================

# --- Device Schemas ---


class DeviceCreate(BaseModel):
    """Schema for creating a new device (linking)."""

    name: Optional[str] = None


class DeviceResponse(BaseModel):
    """Schema for device response."""

    id: uuid.UUID
    device_id: str
    phone: Optional[str] = None
    name: Optional[str] = None
    status: str
    connected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Schema for list of devices."""

    devices: List[DeviceResponse]
    total: int


class QRCodeResponse(BaseModel):
    """Schema for QR code response."""

    device_id: str
    qr_code: Optional[str] = None  # Base64 encoded QR or image URL
    status: str
    message: Optional[str] = None


# --- Message Schemas ---


class SendMessageRequest(BaseModel):
    """Schema for sending a message."""

    phone: str = Field(
        ...,
        pattern=r"^\d{8,15}$",
        description="Phone number with country code (8-15 digits)",
    )
    message: str


class SendMessageResponse(BaseModel):
    """Schema for send message response."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: uuid.UUID
    message_id: str
    from_phone: str
    to_phone: str
    body: Optional[str] = None
    message_type: str
    is_from_me: bool
    status: str
    media_url: Optional[str] = None
    timestamp: datetime
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatSummary(BaseModel):
    """Schema for chat summary (conversation grouped by phone)."""

    phone: str  # The other party's phone number
    device_id: uuid.UUID  # Device this chat belongs to
    device_phone: Optional[str] = None  # Device's phone number
    last_message: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None
    unread_count: int = 0
    total_messages: int = 0
    is_last_from_me: bool = False


class ChatListResponse(BaseModel):
    """Schema for list of chats."""

    chats: List[ChatSummary]
    total: int


class MessageListResponse(BaseModel):
    """Schema for list of messages."""

    messages: List[MessageResponse]
    total: int
    limit: int
    offset: int


# --- Webhook Schemas ---


class WebhookPayload(BaseModel):
    """Schema for incoming webhook from GOWA."""

    type: str  # message, message.ack, etc.
    device_id: Optional[str] = None
    data: dict
