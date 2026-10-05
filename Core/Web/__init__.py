from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .Routers import api_router as api_router


def setup_cors(app: FastAPI) -> None:
    """配置 CORS，仅允许同源或开发环境 localhost:5173。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def setup_request_language(app: FastAPI) -> None:
    """注册请求语言中间件：System 文件键（API 动态提示）按 Accept-Language 返回（与机器人消息语言无关）。"""
    # 函数内导入：Locale 与路由模块同属聚合导入链，保持延迟加载一致
    from .Locale import setup_request_language as setup_middleware

    setup_middleware(app)
