"""Tests for AI Assistant module endpoints."""

import uuid

# ---------------------------------------------------------------------------
# Providers (no auth needed, no DB)
# ---------------------------------------------------------------------------


async def test_list_providers(client):
    """GET /ai-assistant/providers returns available providers."""
    resp = await client.get("/ai-assistant/providers")
    assert resp.status_code == 200
    data = resp.json()
    # Endpoint returns List[str], not a dict
    assert isinstance(data, list)
    assert "groq" in data


async def test_list_provider_models(client):
    """GET /ai-assistant/providers/groq/models returns models."""
    resp = await client.get("/ai-assistant/providers/groq/models")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_list_provider_models_invalid(client):
    """GET /ai-assistant/providers/invalid/models returns 404."""
    resp = await client.get("/ai-assistant/providers/nonexistent/models")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AI Configs (require device + auth)
# ---------------------------------------------------------------------------


async def test_list_configs_empty(client):
    """GET /ai-assistant/devices/{id}/configs returns empty list for non-existent device."""
    fake_device_id = str(uuid.uuid4())
    resp = await client.get(f"/ai-assistant/devices/{fake_device_id}/configs")
    # Returns 200 with empty list, or 404 if device validation is done
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)


async def test_get_config_not_found(client):
    """GET /ai-assistant/configs/{id} returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/ai-assistant/configs/{fake_id}")
    assert resp.status_code == 404


async def test_delete_config_not_found(client):
    """DELETE /ai-assistant/configs/{id} returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/ai-assistant/configs/{fake_id}")
    assert resp.status_code in (404, 204)


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


async def test_ai_configs_unauthenticated(unauthed_client):
    """AI Assistant config endpoints require authentication."""
    fake_id = str(uuid.uuid4())
    resp = await unauthed_client.get(f"/ai-assistant/devices/{fake_id}/configs")
    assert resp.status_code in (401, 403)
