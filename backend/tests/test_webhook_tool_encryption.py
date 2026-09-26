"""Tests for encryption of webhook tool auth values.

Covers the create/update paths in ``webhook_config_router`` and the decryption
(plus legacy plaintext fallback) in ``tool_loader``.
"""

import json
import logging
import uuid
from unittest.mock import patch

from sqlalchemy import text

from app.modules.ai_assistant.encryption import decrypt_api_key
from app.modules.ai_assistant.tool_loader import DynamicToolLoader
from app.modules.ai_assistant.webhook_tools import DynamicWebhookTool

# Matches the fake user injected by tests/conftest.py.
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

AUTH_VALUE = "super-secret-token-123"

_INSERT_LEGACY = text(
    """
    INSERT INTO webhook_tool_configs
    (id, user_id, name, description, webhook_url, method, headers,
     input_schema, auth_type, auth_value_encrypted, timeout_seconds,
     max_retries, is_enabled)
    VALUES
    (:id, :user_id, :name, :description, :webhook_url, :method, :headers,
     :input_schema, :auth_type, :auth_value, :timeout_seconds,
     :max_retries, :is_enabled)
    """
)


def _payload(name="test-tool", auth_value=AUTH_VALUE, **overrides):
    data = {
        "name": name,
        "description": "Test webhook tool",
        "webhook_url": "https://example.com/hook",
        "method": "POST",
        "headers": {},
        "input_schema": {"type": "object", "properties": {}},
        "auth_type": "bearer",
        "auth_value": auth_value,
        "timeout_seconds": 30,
        "max_retries": 3,
        "is_enabled": True,
    }
    data.update(overrides)
    return data


async def _stored_auth_value(db_session, tool_id: str) -> str | None:
    result = await db_session.execute(
        text("SELECT auth_value_encrypted FROM webhook_tool_configs WHERE id = :id"),
        {"id": tool_id},
    )
    return result.scalar()


async def test_create_encrypts_auth_value(client, db_session):
    """Creating a tool stores ciphertext that decrypts back to the original."""
    resp = await client.post("/webhook-tools", json=_payload())
    assert resp.status_code == 201

    stored = await _stored_auth_value(db_session, resp.json()["id"])
    assert stored is not None
    assert stored != AUTH_VALUE
    assert decrypt_api_key(stored) == AUTH_VALUE


async def test_create_without_auth_value_stores_null(client, db_session):
    """A missing/empty credential is stored as NULL, not an encrypted blank."""
    resp = await client.post(
        "/webhook-tools", json=_payload(auth_value=None)
    )
    assert resp.status_code == 201

    assert await _stored_auth_value(db_session, resp.json()["id"]) is None


async def test_update_encrypts_auth_value(client, db_session):
    """Updating a tool encrypts the new credential too."""
    created = await client.post(
        "/webhook-tools", json=_payload(auth_value="initial-secret")
    )
    assert created.status_code == 201
    tool_id = created.json()["id"]

    new_secret = "updated-secret-456"
    resp = await client.put(f"/webhook-tools/{tool_id}", json={"auth_value": new_secret})
    assert resp.status_code == 200

    stored = await _stored_auth_value(db_session, tool_id)
    assert stored is not None
    assert stored != new_secret
    assert decrypt_api_key(stored) == new_secret


async def test_loader_returns_decrypted_auth_value(client, db_session):
    """The dynamic loader hands the decrypted credential to the tool config."""
    resp = await client.post("/webhook-tools", json=_payload())
    assert resp.status_code == 201
    user_id = resp.json()["user_id"]

    captured = []

    def _capture(config):
        captured.append(config)
        return config

    with patch.object(DynamicWebhookTool, "create_tool", side_effect=_capture):
        tools = await DynamicToolLoader.load_tools_for_user(db_session, user_id)

    assert len(tools) == 1
    assert tools[0].auth_value == AUTH_VALUE


async def test_loader_falls_back_to_legacy_plaintext(client, db_session, caplog):
    """A legacy plaintext row still loads, while encrypted rows keep working."""
    # An encrypted tool stored through the API.
    encrypted = await client.post(
        "/webhook-tools", json=_payload(name="encrypted-tool", auth_value=AUTH_VALUE)
    )
    assert encrypted.status_code == 201

    # A legacy row inserted directly with a plaintext credential.
    legacy_secret = "legacy-plaintext-secret"
    legacy_id = uuid.uuid4()
    await db_session.execute(
        _INSERT_LEGACY,
        {
            "id": legacy_id,
            "user_id": TEST_USER_ID,
            "name": "legacy-tool",
            "description": "Legacy plaintext tool",
            "webhook_url": "https://example.com/legacy",
            "method": "POST",
            "headers": json.dumps({}),
            "input_schema": json.dumps({"type": "object", "properties": {}}),
            "auth_type": "bearer",
            "auth_value": legacy_secret,
            "timeout_seconds": 30,
            "max_retries": 3,
            "is_enabled": True,
        },
    )
    await db_session.commit()

    captured = []

    def _capture(config):
        captured.append(config)
        return config

    caplog.set_level(logging.WARNING, logger="app.modules.ai_assistant.tool_loader")
    with patch.object(DynamicWebhookTool, "create_tool", side_effect=_capture):
        tools = await DynamicToolLoader.load_tools_for_user(db_session, TEST_USER_ID)

    assert len(tools) == 2
    values = {config.name: config.auth_value for config in tools}
    assert values["legacy-tool"] == legacy_secret
    assert values["encrypted-tool"] == AUTH_VALUE

    # The warning must not leak the credential.
    assert "Could not decrypt webhook auth value" in caplog.text
    assert legacy_secret not in caplog.text
    assert AUTH_VALUE not in caplog.text
