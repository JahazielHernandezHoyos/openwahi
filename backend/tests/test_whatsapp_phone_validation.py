"""Validation tests for outbound WhatsApp phone numbers."""

import pytest
from pydantic import ValidationError

from app.modules.whatsapp.models import SendMessageRequest


@pytest.mark.parametrize("phone", ["12345678", "573001234567", "123456789012345"])
def test_send_message_request_accepts_e164_digits(phone: str) -> None:
    request = SendMessageRequest(phone=phone, message="Hello")

    assert request.phone == phone


@pytest.mark.parametrize(
    "phone",
    ["", "1234567", "1234567890123456", "abc", "+573001234567", "573 001 234 567"],
)
def test_send_message_request_rejects_invalid_phone(phone: str) -> None:
    with pytest.raises(ValidationError):
        SendMessageRequest(phone=phone, message="Hello")
