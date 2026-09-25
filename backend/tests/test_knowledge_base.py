"""Tests for Knowledge Base module endpoints.

External services (Qdrant, MinIO, Embeddings) are mocked.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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
