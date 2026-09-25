"""
AI Assistant models - Pydantic schemas and SQLAlchemy models.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base

# ==================== SQLAlchemy Models ====================


class AIConfigKnowledgeBase(Base):
    """Many-to-many relationship between AI configs and knowledge bases."""

    __tablename__ = "ai_config_knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_ai_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ai_config_id", "knowledge_base_id", name="uq_ai_config_kb"),
    )


class WhatsAppAIConfigDB(Base):
    """AI configuration. Can be attached to a WhatsApp device or used standalone (e.g. support widget, API)."""

    __tablename__ = "whatsapp_ai_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(String(128), nullable=False, index=True)
    # Human-readable name for standalone configs (e.g. "Support Bot", "Sales Bot")
    name = Column(String(100), nullable=True)
    # Phone number — only required when attached to a WhatsApp device
    phone_number = Column(String(50), nullable=True, index=True)

    # AI Configuration
    provider = Column(String(20), default="llamacpp", nullable=False)
    model = Column(String(100), default="Qwen3.5-0.8B-Q8_0", nullable=False)
    api_key_encrypted = Column(Text, nullable=False)

    # Bot Settings
    is_enabled = Column(Boolean, default=False, nullable=False)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7, nullable=False)
    max_tokens = Column(Integer, default=1000, nullable=False)

    # Advanced Settings
    use_memory = Column(Boolean, default=True, nullable=False)  # Usar historial
    memory_window = Column(Integer, default=10, nullable=False)  # Últimos N mensajes
    auto_enhance_prompt = Column(
        Boolean, default=True, nullable=False
    )  # Mejorar prompt automáticamente

    # RAG / Knowledge Base Settings
    use_knowledge_base = Column(Boolean, default=False, nullable=False)
    rag_top_k = Column(Integer, default=3, nullable=False)  # Number of chunks to retrieve
    rag_min_score = Column(Float, default=0.75, nullable=False)  # Minimum similarity score

    # LangGraph Agent Settings
    use_agent = Column(
        Boolean, default=False, nullable=False
    )  # Use LangGraph agent with dynamic webhook tools

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    knowledge_bases = relationship(
        "KnowledgeBaseDB",
        secondary="ai_config_knowledge_bases",
        lazy="select",
    )
    conversations = relationship(
        "WhatsAppAIConversationDB",
        back_populates="config",
        cascade="all, delete-orphan",
    )

    @property
    def knowledge_base_ids(self) -> List[uuid.UUID]:
        """Extract knowledge base IDs from relationship for Pydantic serialization."""
        return [kb.id for kb in self.knowledge_bases]


class WhatsAppAIConversationDB(Base):
    """Conversation history with AI."""

    __tablename__ = "whatsapp_ai_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_ai_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_phone = Column(String(50), nullable=False, index=True)  # Quien envía el mensaje

    # Metadata
    message_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    config = relationship("WhatsAppAIConfigDB", back_populates="conversations")
    messages = relationship(
        "WhatsAppAIMessageDB",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class WhatsAppAIMessageDB(Base):
    """Individual message in AI conversation."""

    __tablename__ = "whatsapp_ai_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    whatsapp_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Message Content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # AI Metadata (solo para assistant)
    provider = Column(String(20), nullable=True)
    model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("WhatsAppAIConversationDB", back_populates="messages")


class AIUsageRecordDB(Base):
    """Registro de uso de IA por usuario — para tracking de costos del plan Pro."""

    __tablename__ = "ai_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_ai_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_ai_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider = Column(String(20), nullable=False)  # 'bedrock', 'groq', 'openai'
    model = Column(String(100), nullable=False)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(12, 8), nullable=False, default=0)  # costo calculado
    is_managed = Column(Boolean, nullable=False, default=False)  # True = key de la plataforma
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        # Índices compuestos para queries del dashboard
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
    )


class ManagedAIConfigDB(Base):
    """One ordered entry in the platform's managed AI provider chain."""

    __tablename__ = "managed_ai_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position = Column(Integer, unique=True, nullable=False)
    provider_name = Column(String(100), nullable=False)
    base_url = Column(String(2048), nullable=True)
    model = Column(String(200), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    requires_tools = Column(Boolean, default=False, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_healthy = Column(Boolean, default=True, nullable=False)
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    last_probe_at = Column(DateTime(timezone=True), nullable=True)
    last_probe_latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# Public name from the managed-chain specification; keep the shorter alias used
# internally so existing imports remain readable.
ManagedAIDbConfigDB = ManagedAIConfigDB


class ProviderHealthEventDB(Base):
    """Append-only health history for a managed provider entry."""

    __tablename__ = "provider_health_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("managed_ai_config.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(20), nullable=False, index=True)
    error = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class WebhookToolConfigDB(Base):
    """User-defined webhook tool; read and written via SQL in webhook_config_router."""

    __tablename__ = "webhook_tool_configs"
    __table_args__ = (
        Index("ix_webhook_tool_configs_user_name", "user_id", "name", unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    webhook_url = Column(String(2048), nullable=False)
    method = Column(String(10), nullable=False, server_default="POST")
    headers = Column(JSON, nullable=False, server_default="{}")
    input_schema = Column(JSON, nullable=False)
    auth_type = Column(String(20), nullable=True)
    auth_value_encrypted = Column(Text, nullable=True)
    timeout_seconds = Column(Integer, nullable=False, server_default="30")
    max_retries = Column(Integer, nullable=False, server_default="3")
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    requires_confirmation = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


# ==================== Pydantic Schemas ====================


class ManagedAIConfigCreate(BaseModel):
    provider_name: str = Field(min_length=1, max_length=100)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    api_key: Optional[str] = None
    requires_tools: bool = False
    position: Optional[int] = Field(default=None, ge=0)


class ManagedAIConfigUpdate(BaseModel):
    model: Optional[str] = Field(default=None, min_length=1, max_length=200)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    api_key: Optional[str] = None
    requires_tools: Optional[bool] = None
    is_enabled: Optional[bool] = None
    is_healthy: Optional[bool] = None
    position: Optional[int] = Field(default=None, ge=0)


class ManagedAIChainReorder(BaseModel):
    ordered_ids: List[uuid.UUID]


class AIConfigCreate(BaseModel):
    """Schema for creating AI config. Works with or without a WhatsApp device."""

    name: Optional[str] = None
    phone_number: Optional[str] = None  # Only needed when attached to a device
    provider: str = "llamacpp"
    model: str = "Qwen3.5-0.8B-Q8_0"
    api_key: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    use_memory: bool = True
    memory_window: int = 10
    auto_enhance_prompt: bool = True
    # RAG settings
    use_knowledge_base: bool = False
    knowledge_base_ids: List[uuid.UUID] = []
    rag_top_k: int = 3
    rag_min_score: float = 0.75

    @model_validator(mode="after")
    def require_api_key_for_remote_providers(self):
        """Allow keyless local inference while preserving remote-provider validation."""
        if self.provider != "llamacpp" and not self.api_key:
            raise ValueError("api_key is required for remote AI providers")
        return self


class AIConfigUpdate(BaseModel):
    """Schema for updating AI config."""

    name: Optional[str] = None
    phone_number: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    is_enabled: Optional[bool] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    use_memory: Optional[bool] = None
    memory_window: Optional[int] = None
    auto_enhance_prompt: Optional[bool] = None
    # RAG settings
    use_knowledge_base: Optional[bool] = None
    knowledge_base_ids: Optional[List[uuid.UUID]] = None
    rag_top_k: Optional[int] = None
    rag_min_score: Optional[float] = None

    @model_validator(mode="after")
    def require_api_key_when_switching_to_remote_provider(self):
        """Require a new credential when an update explicitly selects a remote provider."""
        if self.provider is not None and self.provider != "llamacpp" and not self.api_key:
            raise ValueError("api_key is required when selecting a remote AI provider")
        return self


class AIConfigResponse(BaseModel):
    """Schema for AI config response."""

    id: uuid.UUID
    device_id: Optional[uuid.UUID]
    name: Optional[str]
    phone_number: Optional[str]
    provider: str
    model: str
    is_enabled: bool
    system_prompt: Optional[str]
    temperature: float
    max_tokens: int
    use_memory: bool
    memory_window: int
    auto_enhance_prompt: bool
    # RAG settings
    use_knowledge_base: bool
    knowledge_base_ids: List[uuid.UUID]
    rag_top_k: int
    rag_min_score: float
    created_at: datetime
    updated_at: Optional[datetime]

    @field_validator("knowledge_base_ids", mode="before")
    @classmethod
    def extract_kb_ids_from_relationship(cls, v, info):
        """Extract knowledge_base_ids from relationship objects or direct list."""
        if not v:
            return []

        # If it's already a list of UUIDs, return as-is
        if isinstance(v, list) and all(isinstance(item, uuid.UUID) for item in v):
            return v

        # If it's a list of strings, convert to UUIDs
        if isinstance(v, list) and all(isinstance(item, str) for item in v):
            return [uuid.UUID(item) for item in v]

        # Otherwise assume it's a list of objects with .id attribute
        if isinstance(v, list):
            return [item.id if hasattr(item, "id") else uuid.UUID(str(item)) for item in v]

        return []

    class Config:
        from_attributes = True


class AIMessageResponse(BaseModel):
    """Schema for AI message response."""

    id: uuid.UUID
    role: str
    content: str
    provider: Optional[str]
    model: Optional[str]
    tokens_used: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class AIConversationResponse(BaseModel):
    """Schema for AI conversation response."""

    id: uuid.UUID
    from_phone: str
    message_count: int
    started_at: datetime
    last_message_at: datetime
    messages: List[AIMessageResponse] = []

    class Config:
        from_attributes = True


class TestMessageRequest(BaseModel):
    """Schema for testing AI response."""

    message: str


class TestMessageResponse(BaseModel):
    """Schema for test message response."""

    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[int] = None
