import pytest


@pytest.fixture
def audio_bytes() -> bytes:
    """Fake audio bytes for testing (100 bytes)."""
    return b"x" * 100


@pytest.fixture
def audio_filename() -> str:
    return "audio.ogg"
