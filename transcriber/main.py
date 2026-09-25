import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import settings
from transcriber import HybridTranscriber, TranscriptionError

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App state ─────────────────────────────────────────────────────────────────
# Inicialización por defecto para que los tests puedan importar la app sin lifespan
transcriber: HybridTranscriber = HybridTranscriber(
    groq_api_key=settings.GROQ_API_KEY,
    whisper_model=settings.WHISPER_MODEL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcriber
    logger.info("Iniciando openwahi-transcriber…")
    transcriber = HybridTranscriber(
        groq_api_key=settings.GROQ_API_KEY,
        whisper_model=settings.WHISPER_MODEL,
    )
    if not transcriber.groq_available:
        logger.warning(
            "GROQ_API_KEY no configurada. Se usará faster-whisper local como único backend."
        )
    yield
    logger.info("Apagando openwahi-transcriber.")


app = FastAPI(
    title="openwahi-transcriber",
    description="Microservicio de transcripción de audio: Groq Whisper + faster-whisper fallback",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "groq_available": transcriber.groq_available,
        "whisper_loaded": transcriber.whisper_loaded,
    }


@app.post("/transcribe", summary="Transcribir audio")
async def transcribe_audio(
    audio: UploadFile = File(..., description="Archivo de audio (ogg, mp3, mp4, wav)"),
    filename: str = Form(default="audio.ogg", description="Nombre del archivo (incluye extensión)"),
):
    """
    Acepta un archivo de audio en `multipart/form-data` y devuelve la transcripción.

    - Intenta primero la API de Groq (whisper-large-v3-turbo, ~2 s).
    - Si Groq falla (rate limit, error 5xx, timeout), usa faster-whisper local (CPU, ~3-5 s).
    - La cabecera `X-Transcription-Source` indica qué backend se usó.
    """
    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="El archivo de audio está vacío.")

    # Respetar el nombre original del archivo subido si no se pasó uno explícito
    effective_filename = filename or audio.filename or "audio.ogg"

    try:
        result = await transcriber.transcribe(audio_bytes, effective_filename)
    except TranscriptionError as exc:
        logger.error("TranscriptionError: %s", exc)
        # 422 si el audio es inválido/corrupto, 503 si es fallo de infraestructura
        err_msg = str(exc).lower()
        is_invalid_audio = any(k in err_msg for k in (
            "invalid", "corrupt", "format", "decode", "ffmpeg", "audio",
            "end of file", "eof", "no such file", "cannot open", "unsupported",
            "not a valid", "failed to open", "moov atom", "errno",
        ))
        status_code = 422 if is_invalid_audio else 503
        raise HTTPException(status_code=status_code, detail=str(exc))

    response_data = {
        "text": result.text,
        "source": result.source,
        "duration_ms": result.duration_ms,
    }

    return JSONResponse(
        content=response_data,
        headers={"X-Transcription-Source": result.source},
    )


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
