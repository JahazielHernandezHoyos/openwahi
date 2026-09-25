"""create knowledge base tables

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2025-01-31 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h7i8j9k0l1m2"
down_revision: Union[str, Sequence[str], None] = "g6h7i8j9k0l1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create knowledge base tables."""

    # 1. knowledge_bases - Container for documents
    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Basic Info
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        # Configuration
        sa.Column(
            "embedding_model",
            sa.String(100),
            server_default="llama-3.2-3b-preview",
            nullable=False,
        ),
        sa.Column("chunk_size", sa.Integer(), server_default="500", nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), server_default="50", nullable=False),
        # Statistics
        sa.Column("total_documents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        # Qdrant Collection
        sa.Column("qdrant_collection", sa.String(100), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["device_id"], ["whatsapp_devices.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_knowledge_bases_user_id", "knowledge_bases", ["user_id"])
    op.create_index("ix_knowledge_bases_device_id", "knowledge_bases", ["device_id"])
    op.create_index("ix_knowledge_bases_is_active", "knowledge_bases", ["is_active"])

    # 2. knowledge_documents - Documents in knowledge base
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        # File Info
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        # Processing Status
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Statistics
        sa.Column("total_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        # Metadata
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_knowledge_documents_knowledge_base_id",
        "knowledge_documents",
        ["knowledge_base_id"],
    )
    op.create_index(
        "ix_knowledge_documents_status",
        "knowledge_documents",
        ["status"],
    )

    # 3. document_chunks - Text chunks with vector references
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Content
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        # Vector Reference
        sa.Column("qdrant_point_id", sa.String(100), nullable=True),
        # Metadata
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("token_count", sa.Integer(), server_default="0", nullable=False),
        # Timestamp
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
    )
    op.create_index(
        "ix_document_chunks_knowledge_base_id",
        "document_chunks",
        ["knowledge_base_id"],
    )

    # 4. knowledge_query_logs - Query analytics
    op.create_table(
        "knowledge_query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Query Info
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("results_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "top_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("query_time_ms", sa.Integer(), nullable=True),
        # Context
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        # Timestamp
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_knowledge_query_logs_knowledge_base_id",
        "knowledge_query_logs",
        ["knowledge_base_id"],
    )
    op.create_index(
        "ix_knowledge_query_logs_user_id",
        "knowledge_query_logs",
        ["user_id"],
    )
    op.create_index(
        "ix_knowledge_query_logs_created_at",
        "knowledge_query_logs",
        ["created_at"],
    )


def downgrade() -> None:
    """Downgrade schema - drop knowledge base tables."""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index("ix_knowledge_query_logs_created_at", table_name="knowledge_query_logs")
    op.drop_index("ix_knowledge_query_logs_user_id", table_name="knowledge_query_logs")
    op.drop_index(
        "ix_knowledge_query_logs_knowledge_base_id", table_name="knowledge_query_logs"
    )
    op.drop_table("knowledge_query_logs")

    op.drop_index("ix_document_chunks_knowledge_base_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_index(
        "ix_knowledge_documents_knowledge_base_id", table_name="knowledge_documents"
    )
    op.drop_table("knowledge_documents")

    op.drop_index("ix_knowledge_bases_is_active", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_device_id", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_user_id", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
