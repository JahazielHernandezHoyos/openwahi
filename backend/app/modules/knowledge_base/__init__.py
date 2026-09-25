"""
Knowledge Base module for RAG (Retrieval Augmented Generation).

This module provides functionality to:
- Upload and process documents (Excel, PDF, CSV, TXT, DOCX)
- Generate embeddings and store in Qdrant vector database
- Search knowledge bases for relevant context
- Integrate with WhatsApp AI bot for RAG-powered responses
"""

from .models import (
    DocumentChunkDB,
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseDB,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeDocumentDB,
    KnowledgeQueryLogDB,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from .service import KnowledgeBaseService

__all__ = [
    "KnowledgeBaseDB",
    "KnowledgeDocumentDB",
    "DocumentChunkDB",
    "KnowledgeQueryLogDB",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "DocumentUploadResponse",
    "DocumentResponse",
    "SearchResult",
    "SearchRequest",
    "SearchResponse",
    "KnowledgeBaseService",
]
