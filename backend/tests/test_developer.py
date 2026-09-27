"""Tests for Developer module endpoints (API tokens + webhooks)."""

import uuid

# ---------------------------------------------------------------------------
# API Tokens
# ---------------------------------------------------------------------------


async def test_list_tokens_empty(client):
    """GET /developer/tokens returns empty list initially."""
    resp = await client.get("/developer/tokens")
    assert resp.status_code == 200
    data = resp.json()
    assert "tokens" in data
    assert isinstance(data["tokens"], list)


async def test_create_token(client):
    """POST /developer/tokens creates a new API token."""
    resp = await client.post("/developer/tokens", json={"name": "Test Token"})
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data  # The raw token is returned only on creation
    assert data["name"] == "Test Token"


async def test_create_and_list_tokens(client):
    """Created tokens appear in the list."""
    # Create
    create_resp = await client.post("/developer/tokens", json={"name": "Listed Token"})
    assert create_resp.status_code == 201

    # List
    list_resp = await client.get("/developer/tokens")
    assert list_resp.status_code == 200
    tokens = list_resp.json()["tokens"]
    names = [t["name"] for t in tokens]
    assert "Listed Token" in names


async def test_delete_token(client):
    """DELETE /developer/tokens/{id} removes a token."""
    # Create
    create_resp = await client.post(
        "/developer/tokens", json={"name": "Delete Me Token"}
    )
    token_id = create_resp.json()["id"]

    # Delete - returns 204 No Content
    del_resp = await client.delete(f"/developer/tokens/{token_id}")
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = await client.get("/developer/tokens")
    token_ids = [t["id"] for t in list_resp.json()["tokens"]]
    assert token_id not in token_ids


async def test_delete_token_not_found(client):
    """DELETE /developer/tokens/{id} returns 404 for non-existent token."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/developer/tokens/{fake_id}")
    assert resp.status_code == 404


async def test_delete_token_malformed_id(client):
    """DELETE /developer/tokens/{id} returns 422 for a malformed UUID."""
    resp = await client.delete("/developer/tokens/not-a-uuid")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Webhook Config
# ---------------------------------------------------------------------------


async def test_get_webhook_config_empty(client):
    """GET /developer/webhook returns 404 when no webhook configured."""
    resp = await client.get("/developer/webhook")
    # The endpoint raises 404 "No webhook configured" if none exists
    assert resp.status_code == 404


async def test_create_webhook_config(client):
    """PUT /developer/webhook creates/updates webhook config."""
    resp = await client.put(
        "/developer/webhook",
        json={
            "url": "https://example.com/webhook",
            "secret": "my-secret",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["has_secret"] is True


async def test_delete_webhook_config(client):
    """DELETE /developer/webhook removes webhook config."""
    # Create first
    await client.put(
        "/developer/webhook",
        json={
            "url": "https://example.com/webhook",
        },
    )

    # Delete - returns 204 No Content
    resp = await client.delete("/developer/webhook")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


async def test_developer_unauthenticated(unauthed_client):
    """Developer endpoints require authentication."""
    resp = await unauthed_client.get("/developer/tokens")
    assert resp.status_code in (401, 403)

    resp = await unauthed_client.get("/developer/webhook")
    assert resp.status_code in (401, 403)
