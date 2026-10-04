"""I18n 管理器：System / Messages 双源语言包、扁平点路径表查找与命名空间隔离。

三层模型（Refactor §5）：
- **System 层**（系统自带，只读）：系统指令、扩展/插件名称与 WebUI 界面文案（`api.*`），
  注册后**不可被覆盖层覆盖**；用户即便在 `Core/Locales/Messages.*.toml` 写入同名键也会被忽略。
- **Messages 层**（用户可改）：其余全部消息文案，会并入覆盖层结果。
- **覆盖层**（用户 `Core/Locales/Messages.*.toml`，可编辑）：只对非 System 键生效，优先级最高。

各层注册时统一展平为「点路径 → 叶子值」扁平表，合并即按优先级 `update`、查找即 `dict.get`；
命名空间按键前缀隔离：`core.*` / `api.*` / `builtin.*` / `ext.<id>.*`。
（语言上下文由 `Context.resolve_locale` 按键命名空间选择：`api.*` 用系统语言，其余用消息语言。）
"""

from __future__ import annotations

from typing import Any

from Core.Logging import logger

from .Context import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


class I18nManager:
    """System / Messages 双源语言包的注册与渲染编排。"""

    def __init__(self) -> None:
        # 各层均为「语言 -> 扁平点路径表」（叶子值为 str 或 list[str]）
        # System 层：系统自带，只读，受保护不可被覆盖
        self._system: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # Messages 层：用户可改的默认文案
        self._messages: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 扩展语言包：语言 -> {命名空间: 扁平表}（`ext.<id>`）
        self._extensions: dict[str, dict[str, dict[str, Any]]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 覆盖层：用户编辑，仅对非系统键生效
        self._override: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 生效目录：语言 -> 合并后的扁平表（System 优先，覆盖层最后）
        self._catalog: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}

    # ===== 注册 =====

    def register_system(self, tables: dict[str, dict[str, Any]]) -> None:
        """注册 System 层语言包（语言 -> 嵌套表），展平入表。"""
        for language in SUPPORTED_LANGUAGES:
            self._system[language] = _flatten(tables.get(language, {}))
        self._rebuild()

    def register_messages(self, tables: dict[str, dict[str, Any]]) -> None:
        """注册 Messages 层语言包（语言 -> 嵌套表），展平入表。"""
        for language in SUPPORTED_LANGUAGES:
            self._messages[language] = _flatten(tables.get(language, {}))
        self._rebuild()

    def register_extension(self, namespace: str, tables: dict[str, dict[str, Any]]) -> None:
        """注册扩展语言包 `Extensions/<id>/Locales/*` → `ext.<id>.*`（可被用户覆盖）。"""
        for language in SUPPORTED_LANGUAGES:
            self._extensions[language][namespace] = _flatten(tables.get(language, {}), prefix=namespace)
        self._rebuild()

    def unregister_extension(self, namespace: str) -> None:
        """注销扩展语言包（卸载/热重载时调用），避免残留旧文案。"""
        for language in SUPPORTED_LANGUAGES:
            self._extensions[language].pop(namespace, None)
        self._rebuild()

    def _rebuild(self) -> None:
        """重建生效目录：System → Messages → 扩展 → 覆盖层；System 键不可被覆盖。"""
        for language in SUPPORTED_LANGUAGES:
            system = self._system[language]
            merged = dict(system)
            for source in (self._messages[language], *self._extensions[language].values(), self._override[language]):
                for key, value in source.items():
                    if key not in system:
                        merged[key] = value
            self._catalog[language] = merged

    # ===== 覆盖层 =====

    def load_override(self, language: str, data: dict[str, Any]) -> None:
        """加载覆盖层语言包（`Core/Locales/Messages.<language>.toml` 解析结果）。"""
        if language not in SUPPORTED_LANGUAGES:
            return
        self._override[language] = _flatten(data)
        self._rebuild()

    # ===== 查询 / 渲染 =====

    def render(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        """按点路径取值并格式化占位符；语言缺失回退默认语言，键缺失返回原文并告警。"""
        language = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        template = self._lookup(language, key)
        if template is None and language != DEFAULT_LANGUAGE:
            template = self._lookup(DEFAULT_LANGUAGE, key)
        if template is None:
            logger.warning(f'Missing translation key [{key}] for language [{language}].')
            return key
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError) as error:
            logger.warning(f'Failed to format translation [{key}]: {error}')
            return template

    def render_value(self, key: str, locale: str | None = None) -> Any:
        """按点路径取原始叶子值（字符串或字符串列表），供消息包兼容层使用。"""
        language = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        value = self._lookup_value(language, key)
        if value is None and language != DEFAULT_LANGUAGE:
            value = self._lookup_value(DEFAULT_LANGUAGE, key)
        if value is None:
            logger.warning(f'Missing translation key [{key}] for language [{language}].')
            return key
        return value

    def _lookup(self, language: str, key: str) -> str | None:
        value = self._catalog[language].get(key)
        return value if isinstance(value, str) else None

    def _lookup_value(self, language: str, key: str) -> Any:
        value = self._catalog[language].get(key)
        return value if isinstance(value, (str, list)) else None

    def has(self, key: str, locale: str | None = None) -> bool:
        """判断键是否存在（默认语言）。"""
        language = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        return key in self._catalog[language]

    def is_protected(self, key: str) -> bool:
        """判断点路径键是否属于 System 层（受保护，用户覆盖无效）。"""
        return key in self._system[DEFAULT_LANGUAGE]


def _flatten(data: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    """把嵌套语言表展平为「点路径 → 叶子值」（字符串或全字符串列表视为叶子）。"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, path))
        elif isinstance(value, str) or (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            result[path] = value
    return result


i18n = I18nManager()
