# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv venv --python 3.12 && \
    uv sync --frozen --no-dev


FROM debian:bookworm-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y libssl3 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1000 notifyapp  \
    && useradd --system --uid 1000 --gid notifyapp --create-home notifyuser

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app/.venv /app/.venv

RUN rm -f /app/.venv/bin/python && \
    ln -s /usr/local/bin/python3.12 /app/.venv/bin/python && \
    ln -sf /usr/local/bin/python3.12 /app/.venv/bin/python3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --chown=notifyuser:notifyapp . .

# COPY --chown=notifyuser:notifyapp entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh

USER notifyuser

EXPOSE 8000

# ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]