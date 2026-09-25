"""
Unit tests for the openwahi-transcriber microservice.

Covers:
  - HybridTranscriber: Groq success path, Groq fallback to whisper-local,
    no-API-key path, and both-fail error path.
  - FastAPI HTTP endpoints: /health and /transcribe.

No real Groq API calls nor faster-whisper model loading are performed —
everything is fully mocked.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Helpers to build mock Groq transcription responses
# ---------------------------------------------------------------------------

def _make_groq_response(text: str = "hello from groq") -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


def _make_whisper_segment(text: str = "hello from whisper") -> MagicMock:
    seg = MagicMock()
    seg.text = text
    return seg


# ---------------------------------------------------------------------------
# TestHybridTranscriberGroqSuccess
# ---------------------------------------------------------------------------

class TestHybridTranscriberGroqSuccess:
    """Groq API key is present and the call succeeds."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key-123")

    @pytest.fixture
    def mock_groq_client(self):
        """AsyncMock that mimics groq.AsyncGroq.audio.transcriptions.create."""
        client = MagicMock()
        client.audio = MagicMock()
        client.audio.transcriptions = MagicMock()
        client.audio.transcriptions.create = AsyncMock(
            return_value=_make_groq_response("hello from groq")
        )
        return client

    @pytest.mark.asyncio
    async def test_groq_called_first(self, audio_bytes, mock_groq_client):
        """With a valid GROQ_API_KEY, Groq is attempted before whisper-local."""
        with (
            patch("groq.AsyncGroq", return_value=mock_groq_client),
            patch("faster_whisper.WhisperModel") as mock_whisper_cls,
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            await t.transcribe(audio_bytes)

            mock_groq_client.audio.transcriptions.create.assert_awaited_once()
            mock_whisper_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_result_has_source_groq(self, audio_bytes, mock_groq_client):
        """Source field must be 'groq' on a successful Groq response."""
        with (
            patch("groq.AsyncGroq", return_value=mock_groq_client),
            patch("faster_whisper.WhisperModel"),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert result.source == "groq"

    @pytest.mark.asyncio
    async def test_result_has_text(self, audio_bytes, mock_groq_client):
        """Transcription text must be non-empty."""
        with (
            patch("groq.AsyncGroq", return_value=mock_groq_client),
            patch("faster_whisper.WhisperModel"),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert result.text  # not empty

    @pytest.mark.asyncio
    async def test_result_has_duration_ms(self, audio_bytes, mock_groq_client):
        """Duration in milliseconds must be a positive integer."""
        with (
            patch("groq.AsyncGroq", return_value=mock_groq_client),
            patch("faster_whisper.WhisperModel"),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert isinstance(result.duration_ms, int)
            assert result.duration_ms > 0


# ---------------------------------------------------------------------------
# TestHybridTranscriberGroqFallback
# ---------------------------------------------------------------------------

class TestHybridTranscriberGroqFallback:
    """Groq fails for various reasons → fallback to whisper-local."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key-123")

    @pytest.fixture
    def mock_whisper_model(self):
        """Mocked faster-whisper WhisperModel that returns one segment."""
        model = MagicMock()
        info = MagicMock()
        info.duration = 1.5
        model.transcribe = MagicMock(
            return_value=([_make_whisper_segment("hello from whisper")], info)
        )
        return model

    @pytest.mark.asyncio
    async def test_groq_rate_limit_falls_to_whisper(
        self, audio_bytes, mock_whisper_model
    ):
        """RateLimitError from Groq triggers whisper-local fallback."""
        import groq as groq_module

        rate_limit_error = groq_module.RateLimitError(
            message="rate limit", response=MagicMock(status_code=429), body={}
        )
        groq_client = MagicMock()
        groq_client.audio.transcriptions.create = AsyncMock(
            side_effect=rate_limit_error
        )

        with (
            patch("groq.AsyncGroq", return_value=groq_client),
            patch(
                "faster_whisper.WhisperModel", return_value=mock_whisper_model
            ),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert result.source == "whisper-local"

    @pytest.mark.asyncio
    async def test_groq_timeout_falls_to_whisper(
        self, audio_bytes, mock_whisper_model
    ):
        """asyncio.TimeoutError from Groq triggers whisper-local fallback."""
        groq_client = MagicMock()
        groq_client.audio.transcriptions.create = AsyncMock(
            side_effect=asyncio.TimeoutError
        )

        with (
            patch("groq.AsyncGroq", return_value=groq_client),
            patch(
                "faster_whisper.WhisperModel", return_value=mock_whisper_model
            ),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert result.source == "whisper-local"

    @pytest.mark.asyncio
    async def test_groq_5xx_falls_to_whisper(
        self, audio_bytes, mock_whisper_model
    ):
        """InternalServerError from Groq triggers whisper-local fallback."""
        import groq as groq_module

        server_error = groq_module.InternalServerError(
            message="internal error", response=MagicMock(status_code=500), body={}
        )
        groq_client = MagicMock()
        groq_client.audio.transcriptions.create = AsyncMock(
            side_effect=server_error
        )

        with (
            patch("groq.AsyncGroq", return_value=groq_client),
            patch(
                "faster_whisper.WhisperModel", return_value=mock_whisper_model
            ),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert result.source == "whisper-local"

    @pytest.mark.asyncio
    async def test_result_source_whisper_local(
        self, audio_bytes, mock_whisper_model
    ):
        """On any Groq failure the result source must be 'whisper-local'."""
        groq_client = MagicMock()
        groq_client.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("generic groq error")
        )

        with (
            patch("groq.AsyncGroq", return_value=groq_client),
            patch(
                "faster_whisper.WhisperModel", return_value=mock_whisper_model
            ),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            assert result.source == "whisper-local"


# ---------------------------------------------------------------------------
# TestHybridTranscriberNoGroqKey
# ---------------------------------------------------------------------------

class TestHybridTranscriberNoGroqKey:
    """No GROQ_API_KEY is set → skip Groq entirely."""

    @pytest.fixture(autouse=True)
    def _no_env(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

    @pytest.fixture
    def mock_whisper_model(self):
        model = MagicMock()
        info = MagicMock()
        info.duration = 1.0
        model.transcribe = MagicMock(
            return_value=([_make_whisper_segment("whisper direct")], info)
        )
        return model

    @pytest.mark.asyncio
    async def test_no_groq_key_uses_whisper_directly(
        self, audio_bytes, mock_whisper_model
    ):
        """Without GROQ_API_KEY the transcriber goes straight to whisper-local."""
        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch(
                "faster_whisper.WhisperModel", return_value=mock_whisper_model
            ),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            result = await t.transcribe(audio_bytes)

            mock_groq_cls.assert_not_called()
            assert result.source == "whisper-local"

    @pytest.mark.asyncio
    async def test_whisper_loaded_lazily(self, audio_bytes, mock_whisper_model):
        """WhisperModel must NOT be instantiated before the first transcribe call."""
        with patch(
            "faster_whisper.WhisperModel", return_value=mock_whisper_model
        ) as mock_whisper_cls:
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            # Model must NOT be loaded at construction time
            mock_whisper_cls.assert_not_called()

            # Only after the first call should the model be loaded
            await t.transcribe(audio_bytes)
            mock_whisper_cls.assert_called_once()


# ---------------------------------------------------------------------------
# TestHybridTranscriberBothFail
# ---------------------------------------------------------------------------

class TestHybridTranscriberBothFail:
    """Both Groq and whisper-local fail → an exception must be raised."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key-123")

    @pytest.mark.asyncio
    async def test_both_fail_raises(self, audio_bytes):
        groq_client = MagicMock()
        groq_client.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("groq down")
        )

        broken_whisper = MagicMock()
        broken_whisper.transcribe = MagicMock(
            side_effect=RuntimeError("whisper down")
        )

        with (
            patch("groq.AsyncGroq", return_value=groq_client),
            patch(
                "faster_whisper.WhisperModel", return_value=broken_whisper
            ),
        ):
            from transcriber import HybridTranscriber

            t = HybridTranscriber()
            with pytest.raises(Exception):
                await t.transcribe(audio_bytes)


# ---------------------------------------------------------------------------
# TestTranscriberHTTPEndpoints
# ---------------------------------------------------------------------------

class TestTranscriberHTTPEndpoints:
    """FastAPI endpoint tests using httpx.AsyncClient."""

    @pytest.fixture
    def mock_transcription_result(self):
        from transcriber import TranscriptionResult

        return TranscriptionResult(
            text="transcribed audio text",
            source="groq",
            duration_ms=250,
        )

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self):
        """GET /health returns 200 with status=ok."""
        import httpx
        from main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "groq_available" in data
        assert "whisper_loaded" in data

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(
        self, audio_bytes, mock_transcription_result
    ):
        """POST /transcribe with a valid audio file returns 200 with text."""
        import httpx
        from main import app

        with patch(
            "main.HybridTranscriber.transcribe",
            new=AsyncMock(return_value=mock_transcription_result),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/transcribe",
                    files={"audio": ("audio.ogg", audio_bytes, "audio/ogg")},
                    data={"filename": "audio.ogg"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert data["text"]  # non-empty
        assert "source" in data
        assert "duration_ms" in data

    @pytest.mark.asyncio
    async def test_transcribe_sets_source_header(
        self, audio_bytes, mock_transcription_result
    ):
        """POST /transcribe response must include X-Transcription-Source header."""
        import httpx
        from main import app

        with patch(
            "main.HybridTranscriber.transcribe",
            new=AsyncMock(return_value=mock_transcription_result),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/transcribe",
                    files={"audio": ("audio.ogg", audio_bytes, "audio/ogg")},
                    data={"filename": "audio.ogg"},
                )

        assert "x-transcription-source" in response.headers
        assert response.headers["x-transcription-source"] in ("groq", "whisper-local")

    @pytest.mark.asyncio
    async def test_transcribe_invalid_no_audio(self):
        """POST /transcribe without the audio field returns 422 Unprocessable Entity."""
        import httpx
        from main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/transcribe", data={})

        assert response.status_code == 422
