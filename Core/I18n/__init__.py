"""
统一 I18n 引擎公共 API。

用法：
    from Core.I18n import text, i18n_text, set_locale
    text('core.events.player_join', player='Steve')          # 立即渲染为 str
    name = i18n_text('builtin.list.name')                    # 延迟求值（str() 时才按语言解析）

语言包加载（读磁盘）由 Bootstrap / Loader 完成，引擎自身不读磁盘（见 Refactor.md §5.1）。
"""

from __future__ import annotations

from typing import Any

from .Context import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, get_locale, normalize_language, set_locale
from .Deferred import DeferredText, i18n_text
from .Manager import I18nManager, i18n


def text(key: str, **kwargs: Any) -> str:
    """按当前上下文语言取译文并格式化占位符（立即求值）。"""
    return i18n.render(key, locale=get_locale(), **kwargs)


def text_value(key: str) -> Any:
    """按当前上下文语言取原始叶子值（字符串或字符串列表），不做占位符格式化。"""
    return i18n.render_value(key, locale=get_locale())


__all__ = [
    'DEFAULT_LANGUAGE',
    'DeferredText',
    'I18nManager',
    'SUPPORTED_LANGUAGES',
    'get_locale',
    'i18n',
    'i18n_text',
    'normalize_language',
    'set_locale',
    'text',
    'text_value',
]
