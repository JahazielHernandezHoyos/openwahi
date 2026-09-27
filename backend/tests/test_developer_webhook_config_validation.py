"""Validation tests for the developer webhook configuration URL."""

import pytest
from pydantic import ValidationError

from app.modules.developer.models import WebhookConfigCreate


@pytest.mark.parametrize(
    "url",
    ["https://example.com/webhook", "http://localhost:8000/webhook"],
)
def test_webhook_config_accepts_http_urls(url: str):
    assert WebhookConfigCreate(url=url).url == url


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "file:///etc/passwd", "not a url"],
)
def test_webhook_config_rejects_non_http_urls(url: str):
    with pytest.raises(ValidationError):
        WebhookConfigCreate(url=url)
