"""WebUI 后端 API 多语言薄封装：委托统一 I18n 引擎（Core/I18n）。

按每次请求的 `Accept-Language` 头解析语言（zh / en），写入 I18n 的**系统语言**上下文
（`api.*` 界面文案专用，与机器人消息语言互不影响）；译文位于
`Core/Locales/System.{zh,en}.toml` 的 `api.*` 段（只读，随核心分发）。
静态界面文案由前端 vue-i18n 处理，不经过本模块。
"""

from fastapi import FastAPI, Request, Response

from Core.I18n import get_system_locale, normalize_language, set_system_locale
from Core.I18n import text as _render

# 保留旧导出名，兼容既有引用
SUPPORTED_LANGUAGES = ('zh', 'en')
API_NAMESPACE = 'api'
DEFAULT_LANGUAGE = 'zh'


def set_current_language(accept_language: str | None) -> None:
    """从 Accept-Language 头解析并设置当前请求的界面语言（如 zh-CN → zh）。"""
    set_system_locale(normalize_language(accept_language))


def get_language() -> str:
    """获取当前请求的界面语言。"""
    return get_system_locale()


def text(key: str, **kwargs) -> str:
    """按当前请求语言取 API 译文并格式化占位符，缺失键回退默认语言。"""
    return _render(f'{API_NAMESPACE}.{key}', **kwargs)


def setup_request_language(app: FastAPI) -> None:
    """注册中间件：把每个请求的 Accept-Language 写入 ContextVar，供 text() 取用。"""

    @app.middleware('http')
    async def request_language_middleware(request: Request, call_next) -> Response:
        set_current_language(request.headers.get('accept-language'))
        return await call_next(request)
