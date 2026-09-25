# openwahi-transcriber

Audio transcription microservice used by the OpenWahi backend for WhatsApp voice notes.
It tries the **Groq Whisper API** (`whisper-large-v3-turbo`) first and falls back to
**local faster-whisper** (CPU, `int8`) when Groq is not configured, rate-limited, returns
a 5xx, or times out.

The backend calls it at `TRANSCRIBER_URL` (default `http://localhost:8001`; the Compose
stack sets `http://transcriber:8001`).

## Endpoints

### `POST /transcribe`

`multipart/form-data`:

| Field      | Type     | Description                                          |
|------------|----------|------------------------------------------------------|
| `audio`    | `file`   | Audio file (`.ogg`, `.mp3`, `.mp4`, `.wav`)          |
| `filename` | `string` | File name including extension (default `audio.ogg`)  |

`200 OK`:

```json
{ "text": "Hello, how are you?", "source": "groq", "duration_ms": 1843 }
```

The `X-Transcription-Source` response header is `groq` or `whisper-local`.
Errors: `400` empty file, `422` invalid/corrupt audio, `503` every backend failed.

### `GET /health`

```json
{ "status": "ok", "groq_available": true, "whisper_loaded": false }
```

`whisper_loaded` becomes `true` once the local model has been loaded (it loads lazily
on the first fallback).

## Configuration

Read from the environment or `transcriber/.env` (see `.env.example`):

| Variable               | Default | Description                                            |
|------------------------|---------|--------------------------------------------------------|
| `GROQ_API_KEY`         | empty   | Groq API key. Empty = always use local faster-whisper. |
| `WHISPER_MODEL`        | `base`  | faster-whisper model: `tiny`, `base`, `small`.         |
| `GROQ_TIMEOUT_SECONDS` | `10.0`  | Timeout for the Groq call.                             |
| `PORT`                 | `8001`  | Port used by `python main.py`.                         |
| `LOG_LEVEL`            | `INFO`  | `DEBUG`, `INFO`, `WARNING`, `ERROR`.                   |

## Run locally

Requires Python 3.12 (same as the Docker image) and `ffmpeg` on the system.

```bash
cd transcriber
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest pytest-asyncio
cp .env.example .env          # optionally set GROQ_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Tests (fully mocked; no Groq calls, no model download):

```bash
python -m pytest tests -q
```

## Docker

```bash
docker build -t openwahi-transcriber transcriber   # pre-downloads the Whisper base model
docker run -d --name openwahi-transcriber -p 8001:8001 \
  -e GROQ_API_KEY=your-groq-key openwahi-transcriber

curl -F "audio=@/path/to/audio.ogg" http://localhost:8001/transcribe
curl http://localhost:8001/health
```

## Notes

- The local model (~300 MB RAM for `base`) is loaded only on the first fallback; with
  Groq alone the process uses ~50 MB.
- faster-whisper inference runs in a thread executor so it does not block the event loop.
- WhatsApp voice notes are `.ogg` (Opus); ffmpeg handles decoding.
