# syntax=docker/dockerfile:1.7

ARG LLAMA_CPP_IMAGE="ghcr.io/ggml-org/llama.cpp:server@sha256:3d03a6c6e02f6bb13c3b441bed420fa99c853d5ffd474112a1de7d9a0457d6bc"
FROM alpine:3.21 AS model-downloader

ARG MODEL_URL="https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q8_0.gguf?download=true"
ARG MODEL_SHA256="0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c"
ARG MODEL_FILENAME="Qwen3.5-0.8B-Q8_0.gguf"

RUN apk add --no-cache ca-certificates curl \
    && mkdir -p /models \
    && curl --fail --location --retry 5 --retry-all-errors \
        --output "/models/${MODEL_FILENAME}" "${MODEL_URL}" \
    && echo "${MODEL_SHA256}  /models/${MODEL_FILENAME}" | sha256sum -c -

FROM ${LLAMA_CPP_IMAGE}

ARG MODEL_FILENAME="Qwen3.5-0.8B-Q8_0.gguf"
COPY --from=model-downloader "/models/${MODEL_FILENAME}" "/models/${MODEL_FILENAME}"

LABEL org.opencontainers.image.title="OpenWahi llama.cpp Qwen3.5-0.8B CPU server" \
      org.opencontainers.image.source="https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF"
