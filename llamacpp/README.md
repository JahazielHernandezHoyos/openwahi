# Local Qwen CPU service

This image packages `Qwen3.5-0.8B-Q8_0.gguf` with the official llama.cpp
OpenAI-compatible server. The model file is downloaded and SHA-256 verified
during the image build, so startup never downloads model weights.

Build arguments: `LLAMA_CPP_IMAGE`, `MODEL_URL`, `MODEL_SHA256`, `MODEL_FILENAME`.

## Compose defaults

The `llamacpp` service is part of both Compose files. Its limits are configurable
through environment variables:

| Variable                 | Default | Meaning                    |
|--------------------------|---------|----------------------------|
| `LLAMACPP_CPUS`          | `4.0`   | CPU limit                  |
| `LLAMACPP_MEMORY_LIMIT`  | `3g`    | Memory limit               |
| `LLAMACPP_CONTEXT_SIZE`  | `4096`  | Context window (tokens)    |
| `LLAMACPP_THREADS`       | `4`     | Inference threads          |
| `LLAMACPP_MAX_TOKENS`    | `512`   | Max generated tokens       |

The server handles one request at a time (`--parallel 1`).

```bash
docker compose -f docker-compose.prod.yml build llamacpp
docker compose -f docker-compose.prod.yml up -d llamacpp
docker compose -f docker-compose.prod.yml exec llamacpp \
  curl --fail --silent http://localhost:8080/health
```

The production file does not publish the port; the backend reaches the server at
`http://llamacpp:8080/v1` (`LLAMACPP_BASE_URL`) over the internal Compose network.
The dev file publishes it on `127.0.0.1:${LLAMACPP_PORT:-8080}`.

## Managed AI

Local Qwen is the default provider for managed (Pro plan) conversations:

```dotenv
MANAGED_AI_PROVIDER=llamacpp
MANAGED_AI_MODEL=Qwen3.5-0.8B-Q8_0
```

The provider forces Qwen non-thinking mode because hidden reasoning can consume
the whole output budget without producing a visible answer on short WhatsApp
replies.

To route managed conversations to Amazon Bedrock instead (requires `BEDROCK_API_KEY`):

```dotenv
MANAGED_AI_PROVIDER=bedrock
MANAGED_AI_MODEL=amazon.nova-lite-v1:0
```
