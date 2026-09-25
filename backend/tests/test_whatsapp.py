"""Tests for WhatsApp module endpoints.

External services (GOWA) are mocked. Database operations are real.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Device CRUD
# ---------------------------------------------------------------------------


async def test_list_devices_empty(client):
    """GET /whatsapp/devices returns empty list initially."""
    resp = await client.get("/whatsapp/devices")
    assert resp.status_code == 200
    data = resp.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)


async def test_create_device(client):
    """POST /whatsapp/devices creates a device (GOWA mocked)."""
    # The service function is a module-level function, not a class method
    mock_device = MagicMock()
    mock_device.model_dump.return_value = {
        "id": str(uuid.uuid4()),
        "device_id": "test-device-001",
        "name": "Test Device",
        "phone": None,
        "status": "pending",
        "connected_at": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    mock_qr = MagicMock()
    mock_qr.model_dump.return_value = {
        "device_id": "test-device-001",
        "qr_code": "data:image/png;base64,fakeqr",
        "status": "pending",
        "message": "Scan QR code",
    }

    with patch(
        "app.modules.whatsapp.router.service.create_device",
        new_callable=AsyncMock,
        return_value=(mock_device, mock_qr),
    ):
        resp = await client.post("/whatsapp/devices", json={"name": "Test Device"})
        assert resp.status_code == 201
        data = resp.json()
        assert "device" in data
        assert "qr" in data


async def test_get_device_not_found(client):
    """GET /whatsapp/devices/{id} returns 404 for non-existent device."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/whatsapp/devices/{fake_id}")
    assert resp.status_code == 404


async def test_delete_device_not_found(client):
    """DELETE /whatsapp/devices/{id} returns 404 for non-existent device."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/whatsapp/devices/{fake_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------


async def test_list_chats_empty(client):
    """GET /whatsapp/chats returns empty list when no messages."""
    resp = await client.get("/whatsapp/chats")
    assert resp.status_code == 200
    data = resp.json()
    assert "chats" in data
    assert data["total"] == 0


async def test_chat_messages_requires_device_id(client):
    """GET /whatsapp/chats/{phone}/messages requires device_id param."""
    resp = await client.get("/whatsapp/chats/573001234567/messages")
    assert resp.status_code == 422  # missing required query param


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------


async def test_webhook_accepts_request(client):
    """POST /whatsapp/webhook accepts requests (no secret configured in test)."""
    # With WHATSAPP_WEBHOOK_SECRET="" (empty), the webhook should accept requests
    resp = await client.post(
        "/whatsapp/webhook",
        json={"event": "message", "data": {}},
    )
    # Should be processed (200) since no webhook secret is configured in tests
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


async def test_devices_unauthenticated(unauthed_client):
    """WhatsApp endpoints require authentication."""
    resp = await unauthed_client.get("/whatsapp/devices")
    assert resp.status_code in (401, 403)
