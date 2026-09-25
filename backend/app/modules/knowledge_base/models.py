"""
Knowledge Base models - SQLAlchemy and Pydantic schemas.
"""

import uuid
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base

# ==================== Enums ====================


class DocumentStatus(StrEnum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FileType(StrEnum):
    """Supported file types."""

    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    DOCX = "docx"
    JSON = "json"


# ==================== SQLAlchemy Models ====================


class KnowledgeBaseDB(Base):
    """Knowledge base - container for documents."""

    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Configuration
    embedding_model = Column(
        String(100), default="llama-3.2-3b-preview", nullable=False
    )
    chunk_size = Column(Integer, default=500, nullable=False)
    chunk_overlap = Column(Integer, default=50, nullable=False)

    # Statistics
    total_documents = Column(Integer, default=0, nullable=False)
    total_chunks = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(BigInteger, default=0, nullable=False)

    # Qdrant Collection Name (derived from id)
    qdrant_collection = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    documents = relationship(
        "KnowledgeDocumentDB",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
    chunks = relationship(
        "DocumentChunkDB",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
    query_logs = relationship(
        "KnowledgeQueryLogDB",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )


class KnowledgeDocumentDB(Base):
    """Document within a knowledge base."""

    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File Info
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(String(500), nullable=False)  # S3/MinIO path
    content_type = Column(String(100), nullable=True)  # MIME type

    # Processing Status
    status = Column(
        String(20), default=DocumentStatus.PENDING.value, nullable=False, index=True
    )
    error_message = Column(Text, nullable=True)

    # Statistics
    total_chunks = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    # Metadata (extracted from document)
    # NOTE: "metadata" is reserved in SQLAlchemy Declarative API, so we must
    # explicitly set key to avoid the conflict.
    doc_metadata = Column(
        "metadata", JSONB, default=dict, nullable=False, key="doc_metadata"
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    knowledge_base = relationship("KnowledgeBaseDB", back_populates="documents")
    chunks = relationship(
        "DocumentChunkDB",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunkDB(Base):
    """Document chunk - text fragment with vector reference."""

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Vector Reference
    qdrant_point_id = Column(String(100), nullable=True)  # UUID in Qdrant

    # Metadata
    chunk_metadata = Column(
        "metadata", JSONB, default=dict, nullable=False, key="chunk_metadata"
    )
    token_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("KnowledgeDocumentDB", back_populates="chunks")
    knowledge_base = relationship("KnowledgeBaseDB", back_populates="chunks")


class KnowledgeQueryLogDB(Base):
    """Query analytics log."""

    __tablename__ = "knowledge_query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(128), nullable=True, index=True)

    # Query Info
    query_text = Column(Text, nullable=False)
    results_count = Column(Integer, default=0, nullable=False)
    top_scores = Column(
        JSONB, default=list, nullable=False
    )  # List of top similarity scores
    query_time_ms = Column(Integer, nullable=True)

    # Context (e.g., WhatsApp conversation ID)
    context = Column(JSONB, default=dict, nullable=False)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    knowledge_base = relationship("KnowledgeBaseDB", back_populates="query_logs")


# ==================== Pydantic Schemas ====================


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    device_id: Optional[uuid.UUID] = None
    embedding_model: str = "llama-3.2-3b-preview"
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    chunk_size: Optional[int] = Field(None, ge=100, le=2000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500)


class KnowledgeBaseResponse(BaseModel):
    """Schema for knowledge base response."""

    id: uuid.UUID
    user_id: str
    device_id: Optional[uuid.UUID]
    name: str
    description: Optional[str]
    is_active: bool
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    total_documents: int
    total_chunks: int
    total_size_bytes: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    error_message: Optional[str]
    total_chunks: int
    total_tokens: int
    metadata: Dict[str, Any] = Field(alias="doc_metadata")
    created_at: datetime
    updated_at: Optional[datetime]
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    id: uuid.UUID
    filename: str
    file_size_bytes: int
    status: str
    message: str


class SearchResult(BaseModel):
    """Schema for a single search result."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    """Schema for search request."""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    knowledge_base_ids: Optional[List[uuid.UUID]] = None  # None = search all active


class SearchResponse(BaseModel):
    """Schema for search response."""

    query: str
    results: List[SearchResult]
    total_results: int
    query_time_ms: int


class ChunkResponse(BaseModel):
    """Schema for chunk response."""

    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: int
    metadata: Dict[str, Any] = Field(alias="chunk_metadata")

    class Config:
        from_attributes = True
        populate_by_name = True
