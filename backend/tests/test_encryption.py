"""Tests for the AI encryption service.

Focus: a missing ``AI_ENCRYPTION_KEY`` triggers a temporary key, but that key
must never be written to the logs (it decrypts every stored provider secret).
"""

import logging

import pytest
from cryptography.fernet import Fernet

from app.modules.ai_assistant.encryption import EncryptionService

LOGGER_NAME = "app.modules.ai_assistant.encryption"


@pytest.fixture
def restore_cipher():
    """Restore the process-wide cipher so later tests keep working."""
    original_cipher = EncryptionService._cipher
    yield
    EncryptionService._cipher = original_cipher


def test_missing_key_warns_without_leaking_it(monkeypatch, caplog, restore_cipher):
    """The temporary key must not appear in any log record."""
    generated_key = Fernet.generate_key().decode()
    monkeypatch.delenv("AI_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(Fernet, "generate_key", lambda: generated_key.encode())
    EncryptionService._cipher = None

    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    encrypted = EncryptionService.encrypt("x")

    # It still warns that the key is missing and a temporary one is in use...
    assert caplog.records
    assert "AI_ENCRYPTION_KEY not set" in caplog.text
    assert "temporary key" in caplog.text

    # ...but the key itself never reaches the logs.
    assert generated_key not in caplog.text
    for record in caplog.records:
        assert generated_key not in record.getMessage()

    # The cipher still works and stays restored by the fixture afterwards.
    assert EncryptionService.decrypt(encrypted) == "x"
