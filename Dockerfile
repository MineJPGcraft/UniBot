FROM python:3.12-alpine AS builder

ENV UV_PYTHON_DOWNLOADS=never \
    UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv sync --no-dev \
    --extra extensions \
    --no-editable \
    --no-cache

# 前端构建阶段：WebUI 源码随核心仓库分发，镜像内构建产物后拷入运行时镜像
FROM oven-sh/bun:1 AS webui-builder

WORKDIR /webui

COPY WebUi/package.json WebUi/bun.lock ./
RUN bun install --frozen-lockfile

COPY WebUi/ ./
RUN bun run build

FROM python:3.12-alpine

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache tini curl

RUN adduser -S -D -s /sbin/nologin worker && mkdir -p /data && chown worker /data

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder --chown=worker:worker /app/.venv /app/.venv
COPY --chown=worker:worker . /app/
# 前端构建产物（镜像内构建，不依赖仓库内是否已提交 dist）
COPY --from=webui-builder --chown=worker:worker /webui/dist /app/WebUi/dist

WORKDIR /app

USER worker

VOLUME ["/data/"]
EXPOSE 8000

ENTRYPOINT ["/sbin/tini", "--", "sh", "/app/entrypoint.sh"]
CMD ["python", "/app/Watchdog.py"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
        CMD curl -f http://127.0.0.1:8000/api/status || exit 1
