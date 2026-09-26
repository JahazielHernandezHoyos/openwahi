"""
Knowledge Base API Router - Endpoints for managing knowledge bases and RAG.
"""

import logging
from typing import List, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.core.dependencies import get_current_user_id

from .models import (
    ChunkResponse,
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from .service import KnowledgeBaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


def _content_disposition(filename: str) -> str:
    """Build an RFC 6266/5987 ``Content-Disposition`` header value.

    Ships an ASCII-only ``filename`` fallback (with quotes and backslashes
    escaped) plus a percent-encoded UTF-8 ``filename*`` so non-ASCII names
    (CJK, emoji, quotes, ...) survive without breaking header encoding.
    """
    ascii_filename = filename.encode("ascii", "ignore").decode("ascii")
    ascii_filename = ascii_filename.replace("\\", "\\\\").replace('"', '\\"')
    if not ascii_filename:
        ascii_filename = "download"
    encoded_filename = quote(filename, safe="")
    return (
        f'attachment; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{encoded_filename}"
    )


# ==================== Knowledge Base Management ====================


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new knowledge base.

    A knowledge base is a container for documents that can be searched
    using RAG (Retrieval Augmented Generation).
    """
    try:
        kb = await KnowledgeBaseService.create_knowledge_base(
            db=db,
            user_id=user_id,
            name=data.name,
            description=data.description,
            device_id=data.device_id,
            embedding_model=data.embedding_model,
            chunk_size=data.chunk_size,
            chunk_overlap=data.chunk_overlap,
        )
        return kb

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    include_inactive: bool = Query(False, description="Include inactive knowledge bases"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    List all knowledge bases for the current user.
    """
    return await KnowledgeBaseService.list_knowledge_bases(
        db=db,
        user_id=user_id,
        include_inactive=include_inactive,
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get a knowledge base by ID.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this knowledge base",
        )

    return kb


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: UUID,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Update a knowledge base.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this knowledge base",
        )

    updates = data.model_dump(exclude_unset=True)
    updated_kb = await KnowledgeBaseService.update_knowledge_base(db, kb_id, **updates)

    return updated_kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a knowledge base and all its documents.

    This action is irreversible.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this knowledge base",
        )

    await KnowledgeBaseService.delete_knowledge_base(db, kb_id)


@router.post("/{kb_id}/toggle")
async def toggle_knowledge_base(
    kb_id: UUID,
    is_active: bool = Query(..., description="New active status"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Toggle a knowledge base active/inactive.

    Inactive knowledge bases won't be searched during RAG queries.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this knowledge base",
        )

    updated_kb = await KnowledgeBaseService.toggle_knowledge_base(db, kb_id, is_active)

    return {
        "success": True,
        "message": f"Knowledge base {'activated' if is_active else 'deactivated'}",
        "knowledge_base": updated_kb,
    }


# ==================== Document Management ====================


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    kb_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Upload a document to a knowledge base.

    Supported file types:
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    - PDF (.pdf)
    - Text (.txt)
    - Markdown (.md)
    - Word (.docx)
    - JSON (.json)

    Maximum file size: 10 MB (configurable)
    """
    # Verify knowledge base ownership
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload to this knowledge base",
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {e}",
        )

    # Upload document
    try:
        doc = await KnowledgeBaseService.upload_document(
            db=db,
            kb_id=kb_id,
            filename=file.filename or "unnamed",
            file_content=file_content,
            content_type=file.content_type,
        )

        return DocumentUploadResponse(
            id=doc.id,
            filename=doc.filename,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status,
            message="Document uploaded and queued for processing",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    List all documents in a knowledge base.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this knowledge base",
        )

    return await KnowledgeBaseService.list_documents(db, kb_id)


@router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    kb_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get a document by ID.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this knowledge base",
        )

    doc = await KnowledgeBaseService.get_document(db, doc_id)

    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return doc


@router.delete(
    "/{kb_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    kb_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a document from a knowledge base.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this knowledge base",
        )

    doc = await KnowledgeBaseService.get_document(db, doc_id)

    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await KnowledgeBaseService.delete_document(db, doc_id)


@router.get("/{kb_id}/documents/{doc_id}/download")
async def download_document(
    kb_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Download the original document file.
    """
    from fastapi.responses import Response
    
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this knowledge base",
        )

    doc = await KnowledgeBaseService.get_document(db, doc_id)

    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Download file content from storage
    try:
        file_content = await KnowledgeBaseService.download_document(db, doc_id)
        
        # Determine content type
        content_type = doc.content_type or "application/octet-stream"
        
        return Response(
            content=file_content,
            media_type=content_type,
            headers={
                "Content-Disposition": _content_disposition(doc.filename),
            },
        )
    except Exception:
        logger.exception("Failed to download document %s", doc_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download document",
        )



@router.post("/{kb_id}/documents/{doc_id}/reprocess")
async def reprocess_document(
    kb_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Reprocess a document (re-chunk and re-embed).

    Useful if chunking settings were changed or processing failed.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this knowledge base",
        )

    doc = await KnowledgeBaseService.get_document(db, doc_id)

    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    success = await KnowledgeBaseService.reprocess_document(db, doc_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reprocess document",
        )

    return {
        "success": True,
        "message": "Document reprocessing started",
    }


@router.get("/{kb_id}/documents/{doc_id}/chunks", response_model=List[ChunkResponse])
async def list_document_chunks(
    kb_id: UUID,
    doc_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    List chunks for a document.

    Useful for debugging and understanding how a document was chunked.
    """
    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this knowledge base",
        )

    doc = await KnowledgeBaseService.get_document(db, doc_id)

    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return await KnowledgeBaseService.list_document_chunks(
        db, doc_id, limit=limit, offset=offset
    )


# ==================== Search / Query ====================


@router.post("/{kb_id}/query", response_model=SearchResponse)
async def query_knowledge_base(
    kb_id: UUID,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Search a specific knowledge base.
    """
    import time

    start_time = time.time()

    kb = await KnowledgeBaseService.get_knowledge_base(db, kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if kb.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to search this knowledge base",
        )

    results = await KnowledgeBaseService.search(
        db=db,
        knowledge_base_ids=[kb_id],
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score,
        user_id=user_id,
    )

    query_time_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        query_time_ms=query_time_ms,
    )


@router.post("/query-all", response_model=SearchResponse)
async def query_all_knowledge_bases(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Search across all active knowledge bases for the current user.

    Optionally filter by specific knowledge base IDs.
    """
    import time

    start_time = time.time()

    results = await KnowledgeBaseService.search_for_user(
        db=db,
        user_id=user_id,
        query=request.query,
        knowledge_base_ids=request.knowledge_base_ids,
        top_k=request.top_k,
        min_score=request.min_score,
    )

    query_time_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        query_time_ms=query_time_ms,
    )
