"""
统一 I18n 引擎：注册 → 合并 → 覆盖 → 点路径查找。

引擎位于 Foundation 层，只依赖标准库，不读磁盘、不 import Core.Config：
语言包由上层（Bootstrap / Loader）解析后注册进引擎。

语言上下文分**两套**，互不影响，按键命名空间自动路由（见 `resolve_locale`）：
- **系统语言**（界面语言）：由 WebUI 每请求的 `Accept-Language` 驱动，作用于界面文案
  命名空间 `api.*`；
- **消息语言**（机器人文案）：由 `Config.toml` 的 `language` 字段驱动，作用于其余全部文案
  （`core.*` / `builtin.*` / `ext.<id>.*`）。

两套语言各由独立 ContextVar 承载：WebUI 请求切换界面语言**不会**影响机器人消息语言。

详见 Refactor.md §5。
"""

from __future__ import annotations

from contextvars import ContextVar

# 支持的语言与默认语言
SUPPORTED_LANGUAGES: tuple[str, ...] = ('zh', 'en')
DEFAULT_LANGUAGE = 'zh'

# 界面文案命名空间：命中这些前缀的键跟随「系统语言」，其余跟随「消息语言」
INTERFACE_NAMESPACES: tuple[str, ...] = ('api',)

# 系统语言（WebUI 界面）：按每请求的 Accept-Language 设置
_system_language: ContextVar[str] = ContextVar('system_language', default=DEFAULT_LANGUAGE)
# 消息语言（机器人消息）：启动时按 Config.toml 的 language 对齐
_messages_language: ContextVar[str] = ContextVar('messages_language', default=DEFAULT_LANGUAGE)


def _normalize(language: str) -> str:
    """未支持的语言回退默认语言。"""
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_system_locale() -> str:
    """获取当前上下文的系统语言（WebUI 界面语言）。"""
    return _system_language.get()


def set_system_locale(language: str) -> None:
    """设置当前上下文的系统语言（WebUI 界面语言），未支持的语言回退默认语言。"""
    _system_language.set(_normalize(language))


def get_messages_locale() -> str:
    """获取当前上下文的消息语言（机器人对外文案语言）。"""
    return _messages_language.get()


def set_messages_locale(language: str) -> None:
    """设置当前上下文的消息语言（机器人对外文案语言），未支持的语言回退默认语言。"""
    _messages_language.set(_normalize(language))


def resolve_locale(key: str) -> str:
    """按点路径键的命名空间选择语言上下文：界面命名空间（`api.*`）用系统语言，其余用消息语言。"""
    namespace = key.split('.', 1)[0]
    return get_system_locale() if namespace in INTERFACE_NAMESPACES else get_messages_locale()


def normalize_language(accept_language: str | None) -> str:
    """从 Accept-Language 头解析语言（如 zh-CN → zh），无法识别时回退默认语言。"""
    for part in (accept_language or '').split(','):
        tag = part.split(';')[0].strip().lower()
        language = next((item for item in SUPPORTED_LANGUAGES if tag.startswith(item)), None)
        if language is not None:
            return language
    return DEFAULT_LANGUAGE
