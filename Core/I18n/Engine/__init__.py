"""
I18n 引擎代码（Foundation 层）：注册 → 合并 → 覆盖 → 点路径查找。

本子包只依赖标准库，**不读磁盘、不 import Core 业务模块**（由
`tests/test_architecture.py::test_i18n_engine_is_dependency_free` 锁定）。
语言包的磁盘加载由上层 `Core.I18n`（`Loader.py`）完成。
"""

from __future__ import annotations

from .Context import (
    DEFAULT_LANGUAGE,
    INTERFACE_NAMESPACES,
    SUPPORTED_LANGUAGES,
    get_messages_locale,
    get_system_locale,
    normalize_language,
    resolve_locale,
    set_messages_locale,
    set_system_locale,
)
from .Deferred import DeferredText, i18n_deferred
from .Manager import I18nManager, i18n

__all__ = [
    'DEFAULT_LANGUAGE',
    'INTERFACE_NAMESPACES',
    'SUPPORTED_LANGUAGES',
    'DeferredText',
    'I18nManager',
    'get_messages_locale',
    'get_system_locale',
    'i18n',
    'i18n_deferred',
    'normalize_language',
    'resolve_locale',
    'set_messages_locale',
    'set_system_locale',
]
