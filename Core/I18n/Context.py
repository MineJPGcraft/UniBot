"""
统一 I18n 引擎：注册 → 合并 → 覆盖 → 点路径查找。

引擎位于 Foundation 层，只依赖标准库，不读磁盘、不 import Core.Config：
语言包由上层（Bootstrap / Loader）解析后注册进引擎，当前语言由 ContextVar 承载
（机器人按 config.language；WebUI 后端按每请求 Accept-Language）。

详见 Refactor.md §5。
"""

from __future__ import annotations

from contextvars import ContextVar

# 支持的语言与默认语言
SUPPORTED_LANGUAGES: tuple[str, ...] = ('zh', 'en')
DEFAULT_LANGUAGE = 'zh'

# 当前语言：按任务上下文隔离（机器人单值；WebUI 按请求设置）
_current_language: ContextVar[str] = ContextVar('current_language', default=DEFAULT_LANGUAGE)


def get_locale() -> str:
    """获取当前上下文语言。"""
    return _current_language.get()


def set_locale(language: str) -> None:
    """设置当前上下文语言，未支持的语言回退默认语言。"""
    _current_language.set(language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE)


def normalize_language(accept_language: str | None) -> str:
    """从 Accept-Language 头解析语言（如 zh-CN → zh），无法识别时回退默认语言。"""
    for part in (accept_language or '').split(','):
        tag = part.split(';')[0].strip().lower()
        language = next((item for item in SUPPORTED_LANGUAGES if tag.startswith(item)), None)
        if language is not None:
            return language
    return DEFAULT_LANGUAGE
