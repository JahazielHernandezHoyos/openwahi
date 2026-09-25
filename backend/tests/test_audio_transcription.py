"""
E2E-style tests for the WhatsApp audio transcription flow.

Scenarios covered:
  1. Webhook audio → type='audio', media_url built with literal codec suffix
  2. Webhook ptt key → same handling as audio
  3. Webhook audio + active AI config → transcribed, message_type='audio_transcribed'
  4. Webhook audio + no AI config → saved as 'audio', AI skipped
  5. Webhook audio + empty transcription → AI skipped
  6. Webhook audio + transcription exception → webhook survives, message saved
  7. Outgoing audio (is_from_me=True) → NOT transcribed
  8. Text message → NOT treated as audio
  9. transcribe_audio() groq success
 10. transcribe_audio() non-groq provider → None
 11. transcribe_audio() Groq raises → None
 12. transcribe_audio() empty response → None
 13. GOWAClient.download_media() returns bytes (httpx patched at module level)
 14. GOWAClient.download_media() raises on HTTP error
 15. Full HTTP webhook endpoint → 200
 16. AUDIO_MESSAGE_TYPES constants check
"""

import io
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import TEST_USER_ID

# ─────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────

def _make_device():
    from app.modules.whatsapp.models import WhatsAppDeviceDB
    return WhatsAppDeviceDB(
        user_id=TEST_USER_ID,
        device_id=f"device-{uuid.uuid4().hex[:8]}",
        instance_port=3000,
        phone="573001234567",
        name="Test device",
        status="connected",
    )


def _make_ai_config(device_id: uuid.UUID, encrypted_key: str):
    from app.modules.ai_assistant.models import WhatsAppAIConfigDB
    return WhatsAppAIConfigDB(
        device_id=device_id,
        user_id=TEST_USER_ID,           # NOT NULL
        phone_number="573001234567",     # NOT NULL
        is_enabled=True,
        provider="groq",
        api_key_encrypted=encrypted_key,
        system_prompt="You are a helpful assistant.",
        model="llama3-70b-8192",
        use_agent=False,
    )


def _audio_payload(from_phone="5491155550001", key="audio", val="statics/media/audio_test.ogg; codecs=opus"):
    return {
        "message_id": f"msg-{uuid.uuid4().hex[:8]}",
        "from": f"{from_phone}@s.whatsapp.net",
        "to": "573001234567@s.whatsapp.net",
        key: val,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "is_from_me": False,
    }


GOWA_BASE = "http://localhost:3000"


# ─────────────────────────────────────────────
# 1. Type / media_url detection
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audio_payload_sets_correct_type_and_media_url(db_session):
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = _audio_payload()

    with patch.object(ws, "gowa_client") as mock_gowa:
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"fake-bytes")
        mock_gowa.send_typing_indicator = AsyncMock()

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert msg.message_type == "audio"
    assert msg.media_url == f"{GOWA_BASE}/statics/media/audio_test.ogg; codecs=opus"


@pytest.mark.asyncio
async def test_ptt_payload_sets_correct_type(db_session):
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = _audio_payload(key="ptt", val="statics/media/ptt_test.ogg; codecs=opus")

    with patch.object(ws, "gowa_client") as mock_gowa:
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"ptt-bytes")
        mock_gowa.send_typing_indicator = AsyncMock()

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert msg.message_type == "audio"
    assert "ptt_test.ogg" in (msg.media_url or "")


@pytest.mark.asyncio
async def test_codec_suffix_preserved_as_part_of_audio_filename(db_session):
    """GOWA's codec suffix is a literal part of the downloadable filename."""
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = _audio_payload(val="statics/media/voice_123.ogg; codecs=opus")

    with patch.object(ws, "gowa_client") as mock_gowa:
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"x")
        mock_gowa.send_typing_indicator = AsyncMock()

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert (msg.media_url or "").endswith("voice_123.ogg; codecs=opus")


# ─────────────────────────────────────────────
# 2. Transcription + AI integration
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audio_transcribed_when_ai_config_active(db_session):
    """
    Active AI config → audio downloaded, transcribed, message_type = 'audio_transcribed',
    body = transcribed text, AI assistant called.
    """
    from app.modules.ai_assistant.encryption import encrypt_api_key
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    ai_config = _make_ai_config(device.id, encrypt_api_key("gsk_fake_test_key_12345678901234567890"))
    db_session.add(ai_config)
    await db_session.commit()

    fake_transcription = "Hola, quiero información sobre los precios"
    payload = _audio_payload()

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        patch("app.modules.ai_assistant.service.AIAssistantService") as mock_ai_cls,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"audio-bytes")
        mock_gowa.send_typing_indicator = AsyncMock()
        mock_gowa.send_message = AsyncMock(return_value={"code": "SUCCESS", "results": {"message_id": "ai-001"}})
        mock_transcribe.return_value = fake_transcription
        # process_incoming_message is called as a classmethod: AIAssistantService.process_incoming_message(...)
        mock_ai_cls.process_incoming_message = AsyncMock(return_value="Claro, te doy info.")

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert msg.message_type == "audio_transcribed", f"Got: {msg.message_type}"
    assert msg.body == fake_transcription
    mock_transcribe.assert_called_once()
    mock_ai_cls.process_incoming_message.assert_called_once()
    # Confirm the AI received the transcribed text
    call_kwargs = mock_ai_cls.process_incoming_message.call_args.kwargs
    assert call_kwargs.get("message_text") == fake_transcription


@pytest.mark.asyncio
async def test_audio_skips_ai_when_no_active_config(db_session):
    """No AI config → audio saved as type='audio', transcription NOT called."""
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = _audio_payload()

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"audio-bytes")
        mock_gowa.send_typing_indicator = AsyncMock()

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert msg.message_type == "audio"
    mock_transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_audio_skips_ai_when_transcription_empty(db_session):
    """Empty transcription → AI not called, message stays type='audio'."""
    from app.modules.ai_assistant.encryption import encrypt_api_key
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    db_session.add(_make_ai_config(device.id, encrypt_api_key("gsk_fake_empty_key_12345678901234")))
    await db_session.commit()

    payload = _audio_payload()

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        patch("app.modules.ai_assistant.service.AIAssistantService") as mock_ai_cls,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"silent-audio")
        mock_gowa.send_typing_indicator = AsyncMock()
        mock_transcribe.return_value = None  # empty
        mock_ai_cls.process_incoming_message = AsyncMock(return_value=None)

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert msg.message_type == "audio"
    mock_ai_cls.process_incoming_message.assert_not_called()


@pytest.mark.asyncio
async def test_audio_exception_during_transcription_does_not_fail_webhook(db_session):
    """Transcription exception → webhook survives, message saved as 'audio'."""
    from app.modules.ai_assistant.encryption import encrypt_api_key
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    db_session.add(_make_ai_config(device.id, encrypt_api_key("gsk_fake_error_key_1234567890123456")))
    await db_session.commit()

    payload = _audio_payload()

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"audio")
        mock_gowa.send_typing_indicator = AsyncMock()
        mock_transcribe.side_effect = Exception("Groq rate limit")

        # Must NOT raise
        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None, "Message must be saved even on transcription failure"
    assert msg.message_type == "audio"


# ─────────────────────────────────────────────
# 3. Outgoing / text edge cases
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outgoing_audio_not_transcribed(db_session):
    """is_from_me=True → download_media and transcribe_audio never called."""
    from app.modules.whatsapp import service as ws

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = _audio_payload()
    payload["is_from_me"] = True
    payload["from"] = "573001234567@s.whatsapp.net"
    payload["to"] = "5491155550001@s.whatsapp.net"

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock()
        mock_gowa.send_typing_indicator = AsyncMock()

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    mock_transcribe.assert_not_called()
    mock_gowa.download_media.assert_not_called()


@pytest.mark.asyncio
async def test_text_message_not_treated_as_audio(db_session):
    """Plain text webhook → message_type='text', no download, no transcription."""
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppMessageDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = {
        "message_id": f"msg-txt-{uuid.uuid4().hex[:8]}",
        "from": "5491155550003@s.whatsapp.net",
        "to": "573001234567@s.whatsapp.net",
        "body": "Hola, ¿cómo estás?",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "is_from_me": False,
    }

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock()
        mock_gowa.send_typing_indicator = AsyncMock()
        mock_gowa.send_message = AsyncMock(return_value={"code": "SUCCESS", "results": {}})

        await ws._process_message_webhook(db_session, device, payload, ws_manager=None)

    from sqlalchemy import select
    result = await db_session.execute(
        select(WhatsAppMessageDB).where(WhatsAppMessageDB.message_id == payload["message_id"])
    )
    msg = result.scalar_one_or_none()
    assert msg is not None
    assert msg.message_type == "text"
    assert msg.body == "Hola, ¿cómo estás?"
    mock_transcribe.assert_not_called()
    mock_gowa.download_media.assert_not_called()


# ─────────────────────────────────────────────
# 4. Unit: transcribe_audio()
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transcribe_audio_groq_success():
    """transcribe_audio() groq path → calls AsyncGroq, returns text."""
    from app.modules.ai_assistant.service import transcribe_audio

    expected_text = "Quiero saber el precio del plan premium"

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.audio = MagicMock()
    mock_client.audio.transcriptions = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=expected_text)

    # AsyncGroq is imported lazily inside the function: patch the module it comes from
    with patch("groq.AsyncGroq", return_value=mock_client):
        result = await transcribe_audio(
            audio_bytes=b"fake ogg content",
            api_key="gsk_fake_key",
            provider="groq",
        )

    assert result == expected_text
    mock_client.audio.transcriptions.create.assert_called_once()
    call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs.get("model") == "whisper-large-v3-turbo"
    assert call_kwargs.get("response_format") == "text"


@pytest.mark.asyncio
async def test_transcribe_audio_non_groq_returns_none():
    from app.modules.ai_assistant.service import transcribe_audio
    result = await transcribe_audio(b"audio", api_key="openai_key", provider="openai")
    assert result is None


@pytest.mark.asyncio
async def test_transcribe_audio_groq_exception_returns_none():
    from app.modules.ai_assistant.service import transcribe_audio

    mock_client = MagicMock()
    mock_client.audio = MagicMock()
    mock_client.audio.transcriptions = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(side_effect=Exception("rate limit"))

    with patch("groq.AsyncGroq", return_value=mock_client):
        result = await transcribe_audio(b"audio", api_key="gsk_key", provider="groq")

    assert result is None


@pytest.mark.asyncio
async def test_transcribe_audio_empty_whitespace_returns_none():
    """Groq returning blank string → transcribe_audio returns None."""
    from app.modules.ai_assistant.service import transcribe_audio

    mock_client = MagicMock()
    mock_client.audio = MagicMock()
    mock_client.audio.transcriptions = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value="   ")

    with patch("groq.AsyncGroq", return_value=mock_client):
        result = await transcribe_audio(b"audio", api_key="gsk_key", provider="groq")

    assert result is None


# ─────────────────────────────────────────────
# 5. Unit: GOWAClient.download_media()
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_media_returns_bytes():
    """download_media() GETs the URL with auth and returns raw bytes."""
    from app.modules.whatsapp.whatsapp_client import GOWAClient

    # GOWAClient(host, port) — no base_url kwarg
    client = GOWAClient(host="localhost", port=3000)
    fake_bytes = b"\x00OGG-AUDIO"

    mock_response = MagicMock()
    mock_response.content = fake_bytes
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_response)

    with patch("app.modules.whatsapp.whatsapp_client.httpx.AsyncClient", return_value=mock_http):
        result = await client.download_media("http://localhost:3000/statics/media/audio.ogg")

    assert result == fake_bytes
    mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_download_media_raises_on_http_error():
    """download_media() propagates httpx.HTTPStatusError on bad response."""
    import httpx

    from app.modules.whatsapp.whatsapp_client import GOWAClient

    client = GOWAClient(host="localhost", port=3000)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )
    )

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_response)

    with patch("app.modules.whatsapp.whatsapp_client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(httpx.HTTPError):
            await client.download_media("http://localhost:3000/statics/media/missing.ogg")


# ─────────────────────────────────────────────
# 6. HTTP endpoint smoke test
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_endpoint_returns_200_for_audio_payload(client, db_session):
    """POST /whatsapp/webhook with audio payload returns 200."""
    from app.modules.whatsapp import service as ws
    from app.modules.whatsapp.models import WhatsAppDeviceDB

    device = _make_device()
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = {
        "type": "message",
        "device_id": device.device_id,
        "data": {
            "message_id": f"wh-{uuid.uuid4().hex[:8]}",
            "from": "5491155550099@s.whatsapp.net",
            "to": f"{device.phone}@s.whatsapp.net",
            "audio": "statics/media/http_test.ogg; codecs=opus",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "is_from_me": False,
        },
    }

    with (
        patch.object(ws, "gowa_client") as mock_gowa,
        patch("app.modules.whatsapp.service.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
    ):
        mock_gowa.base_url = GOWA_BASE
        mock_gowa.download_media = AsyncMock(return_value=b"audio-bytes")
        mock_gowa.send_typing_indicator = AsyncMock()
        mock_transcribe.return_value = None

        response = await client.post(
            "/whatsapp/webhook",
            json=payload,
            headers={"X-Webhook-Secret": ""},
        )

    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"


# ─────────────────────────────────────────────
# 7. Constants
# ─────────────────────────────────────────────

def test_audio_message_type_constants():
    from app.modules.ai_assistant.service import AUDIO_MESSAGE_TYPES

    assert "audio" in AUDIO_MESSAGE_TYPES
    assert "ptt" in AUDIO_MESSAGE_TYPES
    assert "voice" in AUDIO_MESSAGE_TYPES
    assert "text" not in AUDIO_MESSAGE_TYPES
    assert "image" not in AUDIO_MESSAGE_TYPES
