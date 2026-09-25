FROM ghcr.io/astral-sh/uv:0.11.11 AS uv

FROM python:3.12-slim

WORKDIR /app

# The virtualenv lives outside /app so the dev bind mount (./backend:/app) cannot hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=uv /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install exactly the locked production dependencies. The project itself is
# intentionally not packaged: the application is copied into /app below.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini entrypoint.sh ./

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
