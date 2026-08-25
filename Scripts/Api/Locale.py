"""WebUI API 多语言支持。

按每次请求的 Accept-Language 头解析语言（zh / en），与机器人消息包
（Config.toml 的 language 字段、Messages 双语包）完全解耦。
译文存放在 Locales/{zh,en}.json（按域嵌套，键用点路径，如 auth.token_expired），
text() 按当前请求语言取值，缺失时回退中文。
静态界面文案由前端 vue-i18n 处理，不经过本模块。
"""

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response

SUPPORTED_LANGUAGES = ('zh', 'en')
DEFAULT_LANGUAGE = 'zh'

LOCALES_DIR = Path(__file__).parent / 'Locales'

# 每个请求各自隔离，未携带可识别头时回退默认语言
_current_language: ContextVar[str] = ContextVar('current_language', default=DEFAULT_LANGUAGE)


def load_translations(language: str) -> dict[str, Any]:
    """加载指定语言的嵌套翻译表，文件缺失或非法时抛错。"""
    return json.loads((LOCALES_DIR / f'{language}.json').read_text('Utf-8'))


# 启动时一次性加载全部语言到内存
TRANSLATIONS = {language: load_translations(language) for language in SUPPORTED_LANGUAGES}


def set_current_language(accept_language: str | None) -> None:
    """从 Accept-Language 头解析并设置当前请求语言（如 zh-CN → zh）。"""
    for part in (accept_language or '').split(','):
        tag = part.split(';')[0].strip().lower()
        if language := next((item for item in SUPPORTED_LANGUAGES if tag.startswith(item)), None):
            _current_language.set(language)
            return
    _current_language.set(DEFAULT_LANGUAGE)


def get_language() -> str:
    """获取当前请求语言。"""
    return _current_language.get()


def _lookup(table: dict[str, Any], key: str) -> str:
    """按点路径在嵌套表中取字符串叶子。"""
    node: Any = table
    for part in key.split('.'):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f'Missing translation key [{key}] for lookup!')
        node = node[part]
    if not isinstance(node, str):
        raise KeyError(f'Translation key [{key}] is not a string leaf!')
    return node


def text(key: str, **kwargs) -> str:
    """按当前请求语言取译文并格式化占位符，缺失键回退中文。"""
    try:
        template = _lookup(TRANSLATIONS[_current_language.get()], key)
    except KeyError:
        template = _lookup(TRANSLATIONS[DEFAULT_LANGUAGE], key)
    return template.format(**kwargs) if kwargs else template


def setup_request_language(app: FastAPI) -> None:
    """注册中间件：把每个请求的 Accept-Language 写入 ContextVar，供 text() 取用。"""

    @app.middleware('http')
    async def request_language_middleware(request: Request, call_next) -> Response:
        set_current_language(request.headers.get('accept-language'))
        return await call_next(request)
