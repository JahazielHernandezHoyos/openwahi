import io
import time
import logging
import asyncio
import tempfile
import os
from dataclasses import dataclass
from typing import Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    source: Literal["groq", "whisper-local"]
    duration_ms: int


class TranscriptionError(Exception):
    """Raised when all transcription backends fail."""
    pass


class HybridTranscriber:
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        whisper_model: Optional[str] = None,
    ):
        # Si no se pasan valores explícitos, leer del entorno en el momento de la instancia
        # (permite que los tests sobrescriban env vars con monkeypatch antes de instanciar)
        if groq_api_key is None and whisper_model is None:
            from pydantic_settings import BaseSettings
            import os

            self.groq_api_key = os.environ.get("GROQ_API_KEY") or None
            self.whisper_model_name = os.environ.get("WHISPER_MODEL", "base")
        else:
            self.groq_api_key = groq_api_key
            self.whisper_model_name = whisper_model or "base"
        self._whisper_model = None  # lazy load

    @property
    def groq_available(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def whisper_loaded(self) -> bool:
        return self._whisper_model is not None

    def _load_whisper(self):
        """Carga lazy del modelo faster-whisper (solo cuando se necesita)."""
        if self._whisper_model is None:
            logger.info(
                "Cargando modelo faster-whisper '%s' en CPU (compute_type=int8)…",
                self.whisper_model_name,
            )
            from faster_whisper import WhisperModel

            self._whisper_model = WhisperModel(
                self.whisper_model_name,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Modelo faster-whisper cargado correctamente.")
        return self._whisper_model

    async def _transcribe_groq(self, audio_bytes: bytes, filename: str) -> str:
        """Llama a la API de Groq con timeout configurable."""
        from groq import AsyncGroq

        client = AsyncGroq(api_key=self.groq_api_key)
        audio_file = (filename, io.BytesIO(audio_bytes), "audio/ogg")

        # asyncio.wait_for aplica el timeout sobre la corutina de Groq
        from config import settings

        transcription = await asyncio.wait_for(
            client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
                response_format="text",
            ),
            timeout=settings.GROQ_TIMEOUT_SECONDS,
        )
        return str(transcription).strip()

    def _transcribe_whisper(self, audio_bytes: bytes, filename: str) -> str:
        """Transcribe localmente con faster-whisper."""
        model = self._load_whisper()

        # Escribir bytes en archivo temporal para que faster-whisper lo procese via ffmpeg
        suffix = os.path.splitext(filename)[-1] or ".ogg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, _info = model.transcribe(tmp_path, beam_size=5)
            text = " ".join(seg.text for seg in segments).strip()
            return text
        finally:
            os.unlink(tmp_path)

    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.ogg"
    ) -> TranscriptionResult:
        """
        Estrategia híbrida:
        1. Intenta Groq Whisper API (rápido, ~2s).
        2. Si falla (rate limit 429, error 5xx, timeout), fallback a faster-whisper local.
        3. Si ambos fallan, lanza TranscriptionError.
        """
        start = time.monotonic()

        # ── Intento 1: Groq ──────────────────────────────────────────────────
        if self.groq_api_key:
            try:
                text = await self._transcribe_groq(audio_bytes, filename)
                duration_ms = max(1, int((time.monotonic() - start) * 1000))
                logger.info("Transcripción Groq OK — %d ms", duration_ms)
                return TranscriptionResult(
                    text=text, source="groq", duration_ms=duration_ms
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Groq timeout tras %.1fs — usando fallback faster-whisper",
                    (time.monotonic() - start),
                )
            except Exception as exc:
                # Capturamos rate-limit (429), errores 5xx, errores de red, etc.
                logger.warning(
                    "Groq falló (%s: %s) — usando fallback faster-whisper",
                    type(exc).__name__,
                    exc,
                )
        else:
            logger.debug("GROQ_API_KEY no configurada; usando faster-whisper directamente.")

        # ── Intento 2: faster-whisper local ──────────────────────────────────
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None, self._transcribe_whisper, audio_bytes, filename
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("Transcripción faster-whisper OK — %d ms", duration_ms)
            return TranscriptionResult(
                text=text, source="whisper-local", duration_ms=duration_ms
            )
        except Exception as exc:
            logger.error("faster-whisper falló: %s: %s", type(exc).__name__, exc)
            raise TranscriptionError(
                f"Todos los backends de transcripción fallaron. Último error: {exc}"
            ) from exc
