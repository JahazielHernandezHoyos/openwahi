"""Tests for the public widget endpoints.

Covers origin validation for widget tokens: a token restricted with
``allowed_origins`` must reject requests that omit the ``Origin`` header,
must match origins ignoring a trailing slash, and a token without
``allowed_origins`` keeps working with or without an Origin.
"""

import uuid

from app.modules.ai_assistant.models import WhatsAppAIConfigDB
from app.modules.widget.models import WidgetTokenDB

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


async def _seed_token(db_session, *, allowed_origins=None, primary_color="#2563eb"):
    """Create an AI config plus a widget token and return the token."""
    config = WhatsAppAIConfigDB(
        user_id=TEST_USER_ID,
        name="Widget test config",
        api_key_encrypted="test-encrypted-key",
    )
    db_session.add(config)
    await db_session.flush()

    token = WidgetTokenDB(
        user_id=TEST_USER_ID,
        ai_config_id=config.id,
        name="Widget test token",
        token="wgt_" + uuid.uuid4().hex,
        allowed_origins=allowed_origins,
        primary_color=primary_color,
    )
    db_session.add(token)
    await db_session.commit()
    return token


# ---------------------------------------------------------------------------
# GET /widget/config
# ---------------------------------------------------------------------------


async def test_config_allows_matching_origin(client, db_session):
    """A restricted token works when the Origin matches."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com")

    resp = await client.get(
        "/widget/config",
        params={"widget_token": token.token},
        headers={"Origin": "https://shop.example.com"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == token.token
    assert body["primary_color"] == "#2563eb"


async def test_config_rejects_missing_origin(client, db_session):
    """A restricted token is rejected when the Origin header is absent."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com")

    resp = await client.get("/widget/config", params={"widget_token": token.token})

    assert resp.status_code == 404


async def test_config_rejects_wrong_origin(client, db_session):
    """A restricted token is rejected for an origin that is not allowed."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com")

    resp = await client.get(
        "/widget/config",
        params={"widget_token": token.token},
        headers={"Origin": "https://evil.example.com"},
    )

    assert resp.status_code == 404


async def test_config_matches_allowed_entry_with_trailing_slash(client, db_session):
    """An allowed entry stored with a trailing slash still matches."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com/")

    resp = await client.get(
        "/widget/config",
        params={"widget_token": token.token},
        headers={"Origin": "https://shop.example.com"},
    )

    assert resp.status_code == 200


async def test_config_matches_origin_with_trailing_slash(client, db_session):
    """An incoming Origin with a trailing slash matches the stored entry."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com")

    resp = await client.get(
        "/widget/config",
        params={"widget_token": token.token},
        headers={"Origin": "https://shop.example.com/"},
    )

    assert resp.status_code == 200


async def test_config_unrestricted_token_without_origin(client, db_session):
    """A token without allowed_origins works even without an Origin header."""
    token = await _seed_token(db_session, allowed_origins=None)

    resp = await client.get("/widget/config", params={"widget_token": token.token})

    assert resp.status_code == 200
    assert resp.json()["token"] == token.token


async def test_config_unrestricted_token_with_origin(client, db_session):
    """A token without allowed_origins works regardless of the Origin sent."""
    token = await _seed_token(db_session, allowed_origins=None)

    resp = await client.get(
        "/widget/config",
        params={"widget_token": token.token},
        headers={"Origin": "https://anything.example.com"},
    )

    assert resp.status_code == 200


async def test_config_invalid_token_without_origin(client):
    """An unknown token is rejected regardless of the missing Origin."""
    resp = await client.get("/widget/config", params={"widget_token": "wgt_nope"})

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /widget/chat and GET /widget/history
# ---------------------------------------------------------------------------


async def test_chat_rejects_missing_origin(client, db_session):
    """A restricted token cannot spend credits when Origin is missing."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com")

    resp = await client.post(
        "/widget/chat",
        json={
            "visitor_id": "visitor-1",
            "message": "hola",
            "widget_token": token.token,
        },
    )

    assert resp.status_code == 403


async def test_history_rejects_missing_origin(client, db_session):
    """A restricted token cannot read visitor history when Origin is missing."""
    token = await _seed_token(db_session, allowed_origins="https://shop.example.com")

    resp = await client.get(
        "/widget/history",
        params={"widget_token": token.token, "visitor_id": "visitor-1"},
    )

    assert resp.status_code == 404
