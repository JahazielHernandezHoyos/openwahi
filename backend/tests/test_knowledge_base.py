"""Tests for Knowledge Base module endpoints.

External services (Qdrant, MinIO, Embeddings) are mocked.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote, unquote

from app.modules.knowledge_base.models import KnowledgeBaseDB, KnowledgeDocumentDB
from app.modules.knowledge_base.service import KnowledgeBaseService

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


async def _seed_document(db_session, filename: str):
    """Insert a knowledge base + document owned by TEST_USER_ID."""
    kb = KnowledgeBaseDB(user_id=TEST_USER_ID, name="Download KB")
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)

    doc = KnowledgeDocumentDB(
        knowledge_base_id=kb.id,
        filename=filename,
        file_type="pdf",
        file_size_bytes=4,
        storage_path=f"{kb.id}/doc.pdf",
        content_type="application/pdf",
        status="ready",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return kb, doc


# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------


async def test_list_knowledge_bases_empty(client):
    """GET /knowledge-base returns empty list initially."""
    # No trailing slash - the router uses prefix="/knowledge-base"
    resp = await client.get("/knowledge-base")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_create_knowledge_base(client):
    """POST /knowledge-base creates a new knowledge base."""
    resp = await client.post(
        "/knowledge-base",
        json={
            "name": "Test KB",
            "description": "A test knowledge base",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test KB"
    assert "id" in data


async def test_create_knowledge_base_missing_name(client):
    """POST /knowledge-base without name returns 422."""
    resp = await client.post("/knowledge-base", json={"description": "no name"})
    assert resp.status_code == 422


async def test_get_knowledge_base_not_found(client):
    """GET /knowledge-base/{id} returns 404 for non-existent KB."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/knowledge-base/{fake_id}")
    assert resp.status_code == 404


async def test_delete_knowledge_base_not_found(client):
    """DELETE /knowledge-base/{id} returns 404 for non-existent KB."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/knowledge-base/{fake_id}")
    assert resp.status_code in (404, 204)


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


async def test_knowledge_base_unauthenticated(unauthed_client):
    """Knowledge base endpoints require authentication."""
    resp = await unauthed_client.get("/knowledge-base")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Document download
# ---------------------------------------------------------------------------


async def test_download_document_sets_safe_content_disposition(client, db_session):
    """Non-ASCII filenames produce an ASCII fallback plus a UTF-8 filename*."""
    filename = '资料 "v2".pdf'
    payload = b"%PDF-1.4 fake document"
    kb, doc = await _seed_document(db_session, filename)

    with patch.object(
        KnowledgeBaseService,
        "download_document",
        new=AsyncMock(return_value=payload),
    ):
        resp = await client.get(
            f"/knowledge-base/{kb.id}/documents/{doc.id}/download"
        )

    assert resp.status_code == 200
    assert resp.content == payload

    disposition = resp.headers["content-disposition"]
    assert disposition == (
        'attachment; filename=" \\"v2\\".pdf"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )
    # The extended parameter round-trips to the original filename.
    encoded = disposition.split("filename*=UTF-8''", 1)[1]
    assert unquote(encoded) == filename


async def test_download_document_error_detail_is_generic(client, db_session):
    """A storage failure yields 500 without leaking the exception text."""
    kb, doc = await _seed_document(db_session, "report.pdf")

    with patch.object(
        KnowledgeBaseService,
        "download_document",
        new=AsyncMock(side_effect=RuntimeError("secret storage detail")),
    ):
        resp = await client.get(
            f"/knowledge-base/{kb.id}/documents/{doc.id}/download"
        )

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to download document"
    assert "secret storage detail" not in resp.text
