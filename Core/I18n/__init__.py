"""
I18n 子系统统一入口：纯引擎（`Engine/`）+ 磁盘加载器（`Loader.py`）。

用法：
    from Core.I18n import text, i18n_deferred, set_messages_locale
    text('core.events.player_join', player='Steve')          # 立即渲染为 str
    name = i18n_deferred('builtin.list.name')                # 延迟求值（str() 时才按语言解析）

语言分两套上下文（按键来源自动路由）：由 `System.*.toml` 提供的键跟随**系统语言**
（WebUI 每请求 Accept-Language；未显式设置时回退消息语言），由 `Messages.*.toml` 与扩展
语言包提供的键跟随**消息语言**（`Config.toml` 的 `language`）。
两套相互独立：切换 WebUI 界面语言不会改变机器人消息语言。

分层（见 Refactor.md §5）：
- `Core.I18n.Engine`（Foundation）：注册/合并/覆盖/渲染 + 语言上下文，**零依赖、不读磁盘**；
- `Core.I18n.Loader`（Infrastructure）：读 `Core/Locales/*.toml` 注册进引擎、写覆盖层。
本 `__init__` 仅做聚合导出，本身不引入额外依赖。
"""

from __future__ import annotations

from typing import Any

from .Engine import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    DeferredText,
    I18nManager,
    get_messages_locale,
    get_system_locale,
    i18n,
    i18n_deferred,
    normalize_language,
    set_messages_locale,
    set_system_locale,
)
from .Loader import (
    overrides_path,
    read_override,
    register_all,
    register_extension_locales,
    unregister_extension_locales,
    write_override,
)


def text(key: str, **kwargs: Any) -> str:
    """按键来源选取语言上下文取译文并格式化占位符（立即求值）。"""
    return i18n.render(key, **kwargs)


def text_value(key: str) -> Any:
    """按键来源选取语言上下文取原始叶子值（字符串或字符串列表），不做占位符格式化。"""
    return i18n.render_value(key)


__all__ = [
    'DEFAULT_LANGUAGE',
    'DeferredText',
    'I18nManager',
    'SUPPORTED_LANGUAGES',
    'get_messages_locale',
    'get_system_locale',
    'i18n',
    'i18n_deferred',
    'normalize_language',
    'overrides_path',
    'read_override',
    'register_all',
    'register_extension_locales',
    'set_messages_locale',
    'set_system_locale',
    'text',
    'text_value',
    'unregister_extension_locales',
    'write_override',
]
