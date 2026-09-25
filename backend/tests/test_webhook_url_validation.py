"""Validation tests for webhook tool URLs."""

import pytest
from pydantic import ValidationError

from app.modules.ai_assistant.webhook_config_router import (
    WebhookToolConfigCreate,
    WebhookToolConfigUpdate,
)


def create_payload(webhook_url: str) -> dict:
    return {
        "name": "notify",
        "description": "Notify an external service",
        "webhook_url": webhook_url,
        "input_schema": {"type": "object", "properties": {}},
    }


@pytest.mark.parametrize("url", ["https://example.com/hook", "http://localhost:8000/hook"])
def test_webhook_create_accepts_http_urls(url: str):
    assert str(WebhookToolConfigCreate(**create_payload(url)).webhook_url) == url


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd"])
def test_webhook_create_rejects_non_http_urls(url: str):
    with pytest.raises(ValidationError):
        WebhookToolConfigCreate(**create_payload(url))


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd"])
def test_webhook_update_rejects_non_http_urls(url: str):
    with pytest.raises(ValidationError):
        WebhookToolConfigUpdate(webhook_url=url)