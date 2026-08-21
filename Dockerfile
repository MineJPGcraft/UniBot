FROM python:3.12-alpine AS builder

ENV UV_PYTHON_DOWNLOADS=never \
    UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv sync --no-dev \
    --extra webui \
    --extra extensions \
    --no-editable \
    --no-cache

FROM python:3.12-alpine

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache tini curl

RUN adduser -S -D -s /sbin/nologin worker && mkdir -p /data && chown worker /data

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder --chown=worker:worker /app/.venv /app/.venv
COPY --chown=worker:worker . /app/

WORKDIR /app

USER worker

VOLUME ["/data/"]
EXPOSE 8000

ENTRYPOINT ["/sbin/tini", "--", "python", "/app/entrypoint.py"]
CMD ["python", "/app/Watchdog.py"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
        CMD curl -f http://127.0.0.1/api/status || exit 1