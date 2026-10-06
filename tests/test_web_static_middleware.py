"""WebUI 中间件测试：静态资源压缩与缓存策略。

对应 `Core/Web/__init__.py` 的 `setup_compression` / `setup_static_cache_headers`：
远程 / Docker 部署时前端 chunk 的传输体积与缓存行为直接决定路由切换体感。
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.testclient import TestClient

from Core.Web import setup_compression, setup_static_cache_headers


def _make_app() -> FastAPI:
    """构造带中间件的测试应用，覆盖资产 / 页面 / 小响应三类路径。"""
    app = FastAPI()
    setup_static_cache_headers(app)
    setup_compression(app)

    @app.get('/webui/assets/app-abc123.js')
    async def asset() -> PlainTextResponse:
        # 体积超过 STATIC_COMPRESS_MIN_SIZE，确保走压缩分支
        return PlainTextResponse('const x = 1;\n' * 200, media_type='text/javascript')

    @app.get('/webui/')
    async def index() -> HTMLResponse:
        return HTMLResponse('<html><body>ok</body></html>')

    @app.get('/webui/api/tiny')
    async def tiny() -> PlainTextResponse:
        return PlainTextResponse('ok', media_type='application/json')

    return app


def test_hashed_assets_are_compressed_and_immutable():
    """带哈希的 assets/*：响应被 gzip 压缩，且带长期不可变缓存头。"""
    client = TestClient(_make_app())
    response = client.get('/webui/assets/app-abc123.js', headers={'Accept-Encoding': 'gzip'})

    assert response.status_code == 200
    assert response.headers.get('content-encoding') == 'gzip'
    assert response.headers['cache-control'] == 'public, max-age=31536000, immutable'
    # TestClient 会自动解压 content，用响应头里的压缩后长度验证（原始 2600 字节 → 数十字节）
    assert int(response.headers['content-length']) < 200


def test_hashed_assets_cache_header_without_compression():
    """客户端不支持压缩时缓存头依然生效。"""
    client = TestClient(_make_app())
    response = client.get('/webui/assets/app-abc123.js', headers={'Accept-Encoding': 'identity'})

    assert response.headers.get('content-encoding') is None
    assert response.headers['cache-control'] == 'public, max-age=31536000, immutable'


def test_html_pages_are_not_cache_control_immutable():
    """index.html 与前端路由回退页使用 no-cache，保证发版后立即生效。"""
    client = TestClient(_make_app())
    response = client.get('/webui/', headers={'Accept-Encoding': 'gzip'})

    assert response.headers['cache-control'] == 'no-cache'


def test_small_api_response_is_not_compressed():
    """小于压缩阈值的小响应不压缩（避免无收益的压缩开销）。"""
    client = TestClient(_make_app())
    response = client.get('/webui/api/tiny', headers={'Accept-Encoding': 'gzip'})

    assert response.headers.get('content-encoding') is None
    # 非 HTML、非 assets：不注入缓存头，交由各接口自行控制
    assert 'cache-control' not in response.headers


def test_compression_does_not_break_minimum_size_with_cache_middleware():
    """缓存中间件不得把响应变成流式（否则 GZip 的 minimum_size 判定会被绕过）。"""
    client = TestClient(_make_app())
    response = client.get('/webui/assets/app-abc123.js', headers={'Accept-Encoding': 'identity'})

    assert response.headers.get('content-encoding') is None
    assert int(response.headers['content-length']) == len('const x = 1;\n' * 200)
