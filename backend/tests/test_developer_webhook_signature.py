"""Outbound developer webhooks must be verifiable against the raw request body."""

import hashlib
import hmac

import httpx
import pytest

from app.modules.ai_assistant.encryption import EncryptionService
from app.modules.developer import service as developer_service
from app.modules.developer.models import WebhookConfigDB
from app.modules.developer.service import DeveloperService

SECRET = "whsec_test_secret"
USER_ID = "webhook-signature-user"


@pytest.fixture
def captured_requests(monkeypatch):
    requests: list[httpx.Request] = []
    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    monkeypatch.setattr(
        developer_service.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return requests


async def _add_config(db_session) -> None:
    db_session.add(
        WebhookConfigDB(
            user_id=USER_ID,
            url="https://hooks.example.com/events",
            secret=EncryptionService.encrypt(SECRET),
        )
    )
    await db_session.commit()


def _assert_signed_raw_body(request: httpx.Request) -> None:
    body = request.content
    expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert request.headers["X-Webhook-Signature"] == f"sha256={expected}"


@pytest.mark.asyncio
async def test_triggered_webhook_signature_matches_raw_body(db_session, captured_requests):
    await _add_config(db_session)

    sent = await DeveloperService.trigger_webhook(
        db_session, USER_ID, "message.received", {"text": "¿Tienen envío a Bogotá?"}
    )

    assert sent is True
    assert len(captured_requests) == 1
    _assert_signed_raw_body(captured_requests[0])


@pytest.mark.asyncio
async def test_test_webhook_signature_matches_raw_body(db_session, captured_requests):
    await _add_config(db_session)

    result = await DeveloperService.test_webhook(db_session, USER_ID)

    assert result.success is True
    assert len(captured_requests) == 1
    _assert_signed_raw_body(captured_requests[0])
