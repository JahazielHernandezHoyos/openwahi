"""
Knowledge Base Service - Business logic for RAG system.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, BinaryIO, Dict, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import settings

from .embeddings import get_embeddings_generator
from .file_processor import FileProcessor, get_file_processor
from .models import (
    DocumentChunkDB,
    DocumentStatus,
    KnowledgeBaseDB,
    KnowledgeDocumentDB,
    KnowledgeQueryLogDB,
    SearchResult,
)
from .storage import get_storage
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Service for managing knowledge bases and RAG operations."""

    # ==================== Knowledge Base CRUD ====================

    @staticmethod
    async def create_knowledge_base(
        db: AsyncSession,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None,
        embedding_model: str = "llama-3.2-3b-preview",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> KnowledgeBaseDB:
        """
        Create a new knowledge base.

        Args:
            db: Database session
            user_id: Owner user ID
            name: Knowledge base name
            description: Optional description
            device_id: Optional associated device ID
            embedding_model: Model for embeddings
            chunk_size: Chunk size in tokens
            chunk_overlap: Overlap between chunks

        Returns:
            Created knowledge base
        """
        # Check user limits
        count_result = await db.execute(
            select(func.count(KnowledgeBaseDB.id)).where(
                KnowledgeBaseDB.user_id == user_id
            )
        )
        current_count = count_result.scalar() or 0

        if current_count >= settings.KB_MAX_BASES_PER_USER:
            raise ValueError(
                f"Maximum knowledge bases limit reached ({settings.KB_MAX_BASES_PER_USER})"
            )

        # Create knowledge base
        kb = KnowledgeBaseDB(
            user_id=user_id,
            device_id=device_id,
            name=name,
            description=description,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        db.add(kb)
        await db.commit()
        await db.refresh(kb)

        # Set Qdrant collection name
        kb.qdrant_collection = f"kb_{str(kb.id).replace('-', '_')}"
        await db.commit()
        await db.refresh(kb)

        # Create Qdrant collection
        vector_store = get_vector_store()
        await vector_store.create_collection(kb.id)

        logger.info(f"Created knowledge base: {kb.id} for user {user_id}")

        # Final refresh to ensure all attributes are loaded (especially updated_at)
        await db.refresh(kb)

        # Explicitly access all attributes to ensure they're loaded in the session
        _ = kb.id
        _ = kb.user_id
        _ = kb.device_id
        _ = kb.name
        _ = kb.description
        _ = kb.is_active
        _ = kb.embedding_model
        _ = kb.chunk_size
        _ = kb.chunk_overlap
        _ = kb.total_documents
        _ = kb.total_chunks
        _ = kb.total_size_bytes
        _ = kb.qdrant_collection
        _ = kb.created_at
        _ = kb.updated_at

        return kb

    @staticmethod
    async def get_knowledge_base(
        db: AsyncSession,
        kb_id: uuid.UUID,
    ) -> Optional[KnowledgeBaseDB]:
        """Get knowledge base by ID."""
        result = await db.execute(
            select(KnowledgeBaseDB).where(KnowledgeBaseDB.id == kb_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_knowledge_bases(
        db: AsyncSession,
        user_id: str,
        include_inactive: bool = False,
    ) -> List[KnowledgeBaseDB]:
        """List knowledge bases for a user."""
        query = select(KnowledgeBaseDB).where(KnowledgeBaseDB.user_id == user_id)

        if not include_inactive:
            query = query.where(KnowledgeBaseDB.is_active == True)

        query = query.order_by(KnowledgeBaseDB.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_knowledge_base(
        db: AsyncSession,
        kb_id: uuid.UUID,
        **updates,
    ) -> Optional[KnowledgeBaseDB]:
        """Update knowledge base."""
        kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)
        if not kb:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(kb, key):
                setattr(kb, key, value)

        await db.commit()
        await db.refresh(kb)

        logger.info(f"Updated knowledge base: {kb_id}")

        return kb

    @staticmethod
    async def delete_knowledge_base(
        db: AsyncSession,
        kb_id: uuid.UUID,
    ) -> bool:
        """Delete knowledge base and all associated data."""
        kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)
        if not kb:
            return False

        # Delete Qdrant collection
        vector_store = get_vector_store()
        await vector_store.delete_collection(kb_id)

        # Delete files from storage
        storage = get_storage()
        result = await db.execute(
            select(KnowledgeDocumentDB).where(
                KnowledgeDocumentDB.knowledge_base_id == kb_id
            )
        )
        documents = result.scalars().all()

        for doc in documents:
            try:
                await storage.delete_file(doc.storage_path)
            except Exception as e:
                logger.warning(f"Failed to delete file {doc.storage_path}: {e}")

        # Delete from database (cascades to documents, chunks, logs)
        await db.delete(kb)
        await db.commit()

        logger.info(f"Deleted knowledge base: {kb_id}")

        return True

    @staticmethod
    async def toggle_knowledge_base(
        db: AsyncSession,
        kb_id: uuid.UUID,
        is_active: bool,
    ) -> Optional[KnowledgeBaseDB]:
        """Toggle knowledge base active status."""
        return await KnowledgeBaseService.update_knowledge_base(
            db, kb_id, is_active=is_active
        )

    # ==================== Document Management ====================

    @staticmethod
    async def upload_document(
        db: AsyncSession,
        kb_id: uuid.UUID,
        filename: str,
        file_content: bytes,
        content_type: Optional[str] = None,
    ) -> KnowledgeDocumentDB:
        """
        Upload and queue document for processing.

        Args:
            db: Database session
            kb_id: Knowledge base ID
            filename: Original filename
            file_content: File content bytes
            content_type: MIME type

        Returns:
            Created document record
        """
        # Validate knowledge base exists
        kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)
        if not kb:
            raise ValueError("Knowledge base not found")

        # Check file size
        file_size = len(file_content)
        max_size = settings.KB_MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size:
            raise ValueError(
                f"File too large. Maximum size is {settings.KB_MAX_FILE_SIZE_MB} MB"
            )

        # Validate file type
        file_processor = get_file_processor()
        if not file_processor.is_supported(filename):
            raise ValueError(f"Unsupported file type: {filename}")

        # Check document count limit
        doc_count_result = await db.execute(
            select(func.count(KnowledgeDocumentDB.id)).where(
                KnowledgeDocumentDB.knowledge_base_id == kb_id
            )
        )
        current_doc_count = doc_count_result.scalar() or 0

        if current_doc_count >= settings.KB_MAX_DOCS_PER_BASE:
            raise ValueError(
                f"Maximum documents limit reached ({settings.KB_MAX_DOCS_PER_BASE})"
            )

        # Upload to storage
        storage = get_storage()
        storage_path = f"{kb_id}/{uuid.uuid4()}/{filename}"

        import io

        await storage.upload_file(
            io.BytesIO(file_content),
            storage_path,
            content_type,
        )

        # Get file type
        file_type = file_processor.get_file_type(filename)

        # Create document record
        doc = KnowledgeDocumentDB(
            knowledge_base_id=kb_id,
            filename=filename,
            file_type=file_type.value if file_type else "unknown",
            file_size_bytes=file_size,
            storage_path=storage_path,
            content_type=content_type,
            status=DocumentStatus.PENDING.value,
        )

        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        logger.info(f"Uploaded document: {doc.id} to KB {kb_id}")

        # Process document (in real app, this would be a background task)
        await KnowledgeBaseService.process_document(db, doc.id)

        return doc

    @staticmethod
    async def process_document(
        db: AsyncSession,
        doc_id: uuid.UUID,
    ) -> bool:
        """
        Process a document: extract text, chunk, embed, and store vectors.

        Args:
            db: Database session
            doc_id: Document ID

        Returns:
            True if processing succeeded
        """
        # Get document
        result = await db.execute(
            select(KnowledgeDocumentDB)
            .where(KnowledgeDocumentDB.id == doc_id)
            .options(selectinload(KnowledgeDocumentDB.knowledge_base))
        )
        doc = result.scalar_one_or_none()

        if not doc:
            logger.error(f"Document not found: {doc_id}")
            return False

        kb = doc.knowledge_base

        # Update status to processing
        doc.status = DocumentStatus.PROCESSING.value
        await db.commit()

        try:
            # Download file from storage
            storage = get_storage()
            file_content = await storage.download_file(doc.storage_path)

            # Process file
            file_processor = get_file_processor(
                chunk_size=kb.chunk_size,
                chunk_overlap=kb.chunk_overlap,
            )

            chunks_data, doc_metadata = await file_processor.process_file(
                file_content=file_content,
                filename=doc.filename,
            )

            # Update document metadata
            doc.doc_metadata = doc_metadata
            doc.total_chunks = len(chunks_data)
            doc.total_tokens = sum(c.get("token_count", 0) for c in chunks_data)

            # Generate embeddings and store
            embeddings_gen = get_embeddings_generator()
            vector_store = get_vector_store()

            # Create chunks and vectors
            vector_points = []
            total_chunks_created = 0

            for i, chunk_data in enumerate(chunks_data):
                # Generate embedding
                embedding = await embeddings_gen.generate_embedding(
                    chunk_data["content"]
                )

                # Create chunk record
                chunk_id = uuid.uuid4()
                chunk = DocumentChunkDB(
                    id=chunk_id,
                    document_id=doc_id,
                    knowledge_base_id=kb.id,
                    content=chunk_data["content"],
                    chunk_index=i,
                    qdrant_point_id=str(chunk_id),
                    chunk_metadata=chunk_data.get("metadata", {}),
                    token_count=chunk_data.get("token_count", 0),
                )

                db.add(chunk)
                total_chunks_created += 1

                # Prepare vector point
                vector_points.append(
                    {
                        "id": str(chunk_id),
                        "vector": embedding,
                        "payload": {
                            "chunk_id": str(chunk_id),
                            "document_id": str(doc_id),
                            "document_name": doc.filename,
                            "knowledge_base_id": str(kb.id),
                            "content": chunk_data["content"][
                                :500
                            ],  # Truncate for payload
                            "chunk_index": i,
                            **chunk_data.get("metadata", {}),
                        },
                    }
                )

            # Batch upsert vectors to Qdrant
            if vector_points:
                await vector_store.upsert_vectors(kb.id, vector_points)

            # Update document status
            doc.status = DocumentStatus.READY.value
            doc.processed_at = datetime.utcnow()

            # Update knowledge base statistics
            kb.total_documents += 1
            kb.total_chunks += total_chunks_created
            kb.total_size_bytes += doc.file_size_bytes

            await db.commit()

            logger.info(
                f"Processed document {doc_id}: {total_chunks_created} chunks created"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}", exc_info=True)

            # Update status to failed
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(e)
            await db.commit()

            return False

    @staticmethod
    async def get_document(
        db: AsyncSession,
        doc_id: uuid.UUID,
    ) -> Optional[KnowledgeDocumentDB]:
        """Get document by ID."""
        result = await db.execute(
            select(KnowledgeDocumentDB).where(KnowledgeDocumentDB.id == doc_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        kb_id: uuid.UUID,
    ) -> List[KnowledgeDocumentDB]:
        """List documents in a knowledge base."""
        result = await db.execute(
            select(KnowledgeDocumentDB)
            .where(KnowledgeDocumentDB.knowledge_base_id == kb_id)
            .order_by(KnowledgeDocumentDB.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        doc_id: uuid.UUID,
    ) -> bool:
        """Delete a document and its chunks/vectors."""
        result = await db.execute(
            select(KnowledgeDocumentDB)
            .where(KnowledgeDocumentDB.id == doc_id)
            .options(selectinload(KnowledgeDocumentDB.chunks))
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return False

        kb_id = doc.knowledge_base_id

        # Delete vectors from Qdrant
        vector_store = get_vector_store()
        point_ids = [
            chunk.qdrant_point_id for chunk in doc.chunks if chunk.qdrant_point_id
        ]

        if point_ids:
            await vector_store.delete_vectors(kb_id, point_ids)

        # Delete file from storage
        storage = get_storage()
        try:
            await storage.delete_file(doc.storage_path)
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")

        # Update KB statistics
        kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)
        if kb:
            kb.total_documents = max(0, kb.total_documents - 1)
            kb.total_chunks = max(0, kb.total_chunks - doc.total_chunks)
            kb.total_size_bytes = max(0, kb.total_size_bytes - doc.file_size_bytes)

        # Delete from database (cascades to chunks)
        await db.delete(doc)
        await db.commit()

        logger.info(f"Deleted document: {doc_id}")

        return True

    @staticmethod
    async def download_document(
        db: AsyncSession,
        doc_id: uuid.UUID,
    ) -> bytes:
        """Download the original document file from storage."""
        doc = await KnowledgeBaseService.get_document(db, doc_id)

        if not doc:
            raise ValueError("Document not found")

        # Download file from storage
        storage = get_storage()
        try:
            file_content = await storage.download_file(doc.storage_path)
            logger.info(f"Downloaded document: {doc_id}")
            return file_content
        except Exception as e:
            logger.error(f"Failed to download document {doc_id}: {e}")
            raise

    @staticmethod
    async def reprocess_document(
        db: AsyncSession,
        doc_id: uuid.UUID,
    ) -> bool:
        """Reprocess a document (delete chunks and re-process)."""
        result = await db.execute(
            select(KnowledgeDocumentDB)
            .where(KnowledgeDocumentDB.id == doc_id)
            .options(selectinload(KnowledgeDocumentDB.chunks))
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return False

        kb_id = doc.knowledge_base_id

        # Delete existing vectors
        vector_store = get_vector_store()
        point_ids = [
            chunk.qdrant_point_id for chunk in doc.chunks if chunk.qdrant_point_id
        ]

        if point_ids:
            await vector_store.delete_vectors(kb_id, point_ids)

        # Delete existing chunks
        await db.execute(
            delete(DocumentChunkDB).where(DocumentChunkDB.document_id == doc_id)
        )

        # Update KB statistics
        kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)
        if kb:
            kb.total_chunks = max(0, kb.total_chunks - doc.total_chunks)

        # Reset document
        doc.status = DocumentStatus.PENDING.value
        doc.total_chunks = 0
        doc.total_tokens = 0
        doc.error_message = None
        doc.processed_at = None

        await db.commit()

        # Reprocess
        return await KnowledgeBaseService.process_document(db, doc_id)

    # ==================== Search / Query ====================

    @staticmethod
    async def search(
        db: AsyncSession,
        knowledge_base_ids: List[uuid.UUID],
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search across knowledge bases.

        Args:
            db: Database session
            knowledge_base_ids: List of KB IDs to search
            query: Search query
            top_k: Number of results
            min_score: Minimum similarity score
            user_id: Optional user ID for logging
            api_key: Optional API key for embeddings (uses user's key)

        Returns:
            List of search results
        """
        start_time = time.time()

        # Generate query embedding using provided API key (user's key)
        embeddings_gen = get_embeddings_generator(api_key=api_key)
        query_vector = await embeddings_gen.generate_embedding(query)

        # Search vectors
        vector_store = get_vector_store()
        raw_results = await vector_store.search_multiple_collections(
            knowledge_base_ids=knowledge_base_ids,
            query_vector=query_vector,
            top_k=top_k,
            min_score=min_score,
        )

        # Convert to search results
        results = []
        for raw in raw_results:
            payload = raw.get("payload", {})
            results.append(
                SearchResult(
                    chunk_id=uuid.UUID(payload.get("chunk_id", raw["id"])),
                    document_id=uuid.UUID(payload.get("document_id")),
                    document_name=payload.get("document_name", "Unknown"),
                    content=payload.get("content", ""),
                    score=raw["score"],
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k
                        not in ("chunk_id", "document_id", "document_name", "content")
                    },
                )
            )

        query_time_ms = int((time.time() - start_time) * 1000)

        # Log query for analytics
        if knowledge_base_ids:
            for kb_id in knowledge_base_ids:
                log = KnowledgeQueryLogDB(
                    knowledge_base_id=kb_id,
                    user_id=user_id,
                    query_text=query,
                    results_count=len(results),
                    top_scores=[r.score for r in results[:5]],
                    query_time_ms=query_time_ms,
                )
                db.add(log)

            await db.commit()

        logger.info(f"Search completed: {len(results)} results in {query_time_ms}ms")

        return results

    @staticmethod
    async def search_for_device(
        db: AsyncSession,
        device_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[SearchResult]:
        """
        Search knowledge bases associated with a device.

        Args:
            db: Database session
            device_id: Device ID
            query: Search query
            top_k: Number of results
            min_score: Minimum similarity score

        Returns:
            List of search results
        """
        # Find active knowledge bases for device
        result = await db.execute(
            select(KnowledgeBaseDB).where(
                KnowledgeBaseDB.device_id == device_id,
                KnowledgeBaseDB.is_active == True,
            )
        )
        knowledge_bases = result.scalars().all()

        if not knowledge_bases:
            return []

        kb_ids = [kb.id for kb in knowledge_bases]

        return await KnowledgeBaseService.search(
            db=db,
            knowledge_base_ids=kb_ids,
            query=query,
            top_k=top_k,
            min_score=min_score,
        )

    @staticmethod
    async def search_for_user(
        db: AsyncSession,
        user_id: str,
        query: str,
        knowledge_base_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[SearchResult]:
        """
        Search knowledge bases for a user.

        Args:
            db: Database session
            user_id: User ID
            query: Search query
            knowledge_base_ids: Optional specific KB IDs (must belong to user)
            top_k: Number of results
            min_score: Minimum similarity score

        Returns:
            List of search results
        """
        if knowledge_base_ids:
            # Verify KBs belong to user
            result = await db.execute(
                select(KnowledgeBaseDB).where(
                    KnowledgeBaseDB.id.in_(knowledge_base_ids),
                    KnowledgeBaseDB.user_id == user_id,
                    KnowledgeBaseDB.is_active == True,
                )
            )
            kbs = result.scalars().all()
            kb_ids = [kb.id for kb in kbs]
        else:
            # Search all user's active KBs
            result = await db.execute(
                select(KnowledgeBaseDB).where(
                    KnowledgeBaseDB.user_id == user_id,
                    KnowledgeBaseDB.is_active == True,
                )
            )
            kbs = result.scalars().all()
            kb_ids = [kb.id for kb in kbs]

        if not kb_ids:
            return []

        return await KnowledgeBaseService.search(
            db=db,
            knowledge_base_ids=kb_ids,
            query=query,
            top_k=top_k,
            min_score=min_score,
            user_id=user_id,
        )

    # ==================== Chunk Operations ====================

    @staticmethod
    async def get_chunk(
        db: AsyncSession,
        chunk_id: uuid.UUID,
    ) -> Optional[DocumentChunkDB]:
        """Get a chunk by ID."""
        result = await db.execute(
            select(DocumentChunkDB).where(DocumentChunkDB.id == chunk_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_document_chunks(
        db: AsyncSession,
        doc_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentChunkDB]:
        """List chunks for a document."""
        result = await db.execute(
            select(DocumentChunkDB)
            .where(DocumentChunkDB.document_id == doc_id)
            .order_by(DocumentChunkDB.chunk_index)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
