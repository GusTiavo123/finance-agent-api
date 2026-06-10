FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

RUN groupadd --system appgroup && useradd --system --gid appgroup appuser

WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/app ./app

RUN mkdir -p /data/governance && chown -R appuser:appgroup /data/governance

ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
