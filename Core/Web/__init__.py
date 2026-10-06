from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .Routers import api_router as api_router

# 静态资源（/webui/assets/*）命中压缩的最小体积：小于 1 kB 的响应压缩收益不足
STATIC_COMPRESS_MIN_SIZE = 1024


def setup_cors(app: FastAPI) -> None:
    """配置 CORS，仅允许同源或开发环境 localhost:5173。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def setup_compression(app: FastAPI) -> None:
    """
    启用响应压缩（gzip / br），显著降低远程 / Docker 部署下前端的传输体积
    （实测各 chunk 可压缩到原始体积的约 1/3）。
    """
    from starlette.middleware.gzip import GZipMiddleware

    app.add_middleware(GZipMiddleware, minimum_size=STATIC_COMPRESS_MIN_SIZE)


def setup_request_language(app: FastAPI) -> None:
    """注册请求语言中间件：System 文件键（API 动态提示）按 Accept-Language 返回（与机器人消息语言无关）。"""
    # 函数内导入：Locale 与路由模块同属聚合导入链，保持延迟加载一致
    from .Locale import setup_request_language as setup_middleware

    setup_middleware(app)


def setup_static_cache_headers(app: FastAPI) -> None:
    """
    设置 WebUI 静态资源的缓存策略：

    - `/webui/assets/*`：文件名带内容哈希，可长期强缓存（路由切换时直接从磁盘缓存取）；
    - 前端其它响应（index.html 与前端路由回退页）：`no-cache`，保证发版后立即生效。

    ⚠️ 用**纯 ASGI 中间件**而非 `@app.middleware('http')`：后者基于 BaseHTTPMiddleware，
    会把响应包装成流式（`more_body=True`），使 GZipMiddleware 跳过 `minimum_size` 判定、
    连几百字节的响应也压缩。
    """
    from starlette.datastructures import MutableHeaders

    class StaticCacheHeadersMiddleware:
        """为静态资源响应补充 Cache-Control（不改变响应体与流式语义）。"""

        def __init__(self, asgi_app) -> None:
            self.app = asgi_app

        async def __call__(self, scope, receive, send) -> None:
            if scope['type'] != 'http':
                await self.app(scope, receive, send)
                return

            is_hashed_asset = str(scope.get('path', '')).startswith('/webui/assets/')

            async def send_with_cache_headers(message) -> None:
                if message['type'] == 'http.response.start':
                    headers = MutableHeaders(scope=message)
                    is_html = headers.get('content-type', '').startswith('text/html')
                    if 'cache-control' not in headers:
                        if is_hashed_asset:
                            headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                        elif is_html:
                            headers['Cache-Control'] = 'no-cache'
                await send(message)

            await self.app(scope, receive, send_with_cache_headers)

    app.add_middleware(StaticCacheHeadersMiddleware)
