"""I18n 管理器：System / Messages 双源语言包、命名空间隔离与点路径渲染。

三层模型（Refactor §5）：
- **System 层**（系统自带，只读）：系统指令与扩展/插件名称，注册后**不可被覆盖层覆盖**；
  用户即便在 `Core/Locales/Messages.*.toml` 写入同名键也会被忽略（`is_protected` 为真）。
- **Messages 层**（用户可改）：其余全部消息文案，会并入覆盖层结果。
- **覆盖层**（用户 `Core/Locales/Messages.*.toml`，可编辑）：只对非 System 键生效，优先级最高。

命名空间按顶层段隔离：`core.*` / `api.*` / `builtin.*` / `ext.<id>.*`。
"""

from __future__ import annotations

from typing import Any

from Core.Logging import logger

from .Catalog import Catalog
from .Context import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


class I18nManager:
    """System / Messages 双源语言包的注册与渲染编排。"""

    def __init__(self) -> None:
        # System 层：语言 -> 嵌套表（系统自带，只读，受保护不可被覆盖）
        self._system: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # Messages 层：语言 -> 嵌套表（用户可改的默认文案）
        self._messages: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 扩展语言包：语言 -> {命名空间: 嵌套表}（`ext.<id>`）
        self._extensions: dict[str, dict[str, dict[str, Any]]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 覆盖层：语言 -> 嵌套表（用户编辑，仅对非系统键生效）与其原始文本
        self._override: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        self._override_raw: dict[str, str] = {language: '' for language in SUPPORTED_LANGUAGES}
        # 已展开的只读目录：语言 -> Catalog（System 优先于 Messages，再叠加覆盖层）
        self._catalog: dict[str, Catalog] = {language: Catalog() for language in SUPPORTED_LANGUAGES}

    # ===== 注册 =====

    def register_system(self, tables: dict[str, dict[str, Any]]) -> None:
        """注册 System 层语言包（语言 -> 嵌套表，已含 `core.*` / `builtin.*` 等命名空间）。"""
        for language in SUPPORTED_LANGUAGES:
            self._system[language] = tables.get(language, {})
        self._rebuild()

    def register_messages(self, tables: dict[str, dict[str, Any]]) -> None:
        """注册 Messages 层语言包（语言 -> 嵌套表，已含 `core.*` / `api.*` 等命名空间）。"""
        for language in SUPPORTED_LANGUAGES:
            self._messages[language] = tables.get(language, {})
        self._rebuild()

    def register_extension(self, namespace: str, tables: dict[str, dict[str, Any]]) -> None:
        """注册扩展语言包 `Extensions/<id>/Locales/*` → `ext.<id>.*`（可被用户覆盖）。"""
        for language in SUPPORTED_LANGUAGES:
            self._extensions[language][namespace] = tables.get(language, {})
        self._rebuild()

    def unregister_extension(self, namespace: str) -> None:
        """注销扩展语言包（卸载/热重载时调用），避免残留旧文案。"""
        for language in SUPPORTED_LANGUAGES:
            self._extensions[language].pop(namespace, None)
        self._rebuild()

    def _rebuild(self) -> None:
        """重建只读目录：System 层 → Messages 层 → 扩展层 → 覆盖层（仅非系统键）。"""
        for language in SUPPORTED_LANGUAGES:
            catalog = Catalog()
            catalog.merge(self._system[language])
            catalog.merge(_strip_protected(self._messages[language], self._system[language]))
            for namespace in self._extensions[language]:
                table = self._extensions[language][namespace]
                if table:
                    catalog.merge(_nest_namespace(namespace, table))
            safe_override = _strip_protected(self._override[language], self._system[language])
            catalog.merge(safe_override)
            self._catalog[language] = catalog

    # ===== 覆盖层 =====

    def load_override(self, language: str, data: dict[str, Any], raw: str = '') -> None:
        """加载覆盖层语言包（`Core/Locales/Messages.<language>.toml` 解析结果）。"""
        if language not in SUPPORTED_LANGUAGES:
            return
        self._override[language] = data
        self._override_raw[language] = raw
        self._rebuild()

    def read_override(self, language: str) -> str:
        """读取覆盖层原始文本。"""
        return self._override_raw.get(language, '')

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
        try:
            return self._catalog[language].lookup(key)
        except KeyError:
            return None

    def _lookup_value(self, language: str, key: str) -> Any:
        try:
            return self._catalog[language].lookup_value(key)
        except KeyError:
            return None

    def has(self, key: str, locale: str | None = None) -> bool:
        """判断键是否存在（默认语言）。"""
        language = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        return self._catalog[language].contains(key)

    def is_protected(self, key: str) -> bool:
        """判断点路径键是否属于 System 层（受保护，用户覆盖无效）。"""
        return _lookup_system(self._system[DEFAULT_LANGUAGE], key) is not None

    def protected_keys(self, locale: str | None = None) -> set[str]:
        """返回 System 层全部展平键（供 WebUI 标记只读），按所选语言。"""
        language = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        return set(_flatten_keys(self._system[language]))

    def available_keys(self, locale: str | None = None) -> dict[str, Any]:
        """返回某语言全部展平键（System + Messages + 扩展 + 生效覆盖），供 WebUI 编辑器展示。"""
        language = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        return self._catalog[language].flattened()


def _nest_namespace(namespace: str, table: dict[str, Any]) -> dict[str, Any]:
    """把命名空间（可含点，如 `ext.Demo`）包在语言表外层，供点路径查找。"""
    node: Any = table
    for part in reversed(namespace.split('.')):
        node = {part: node}
    return node


def _lookup_system(system: dict[str, Any], key: str) -> Any:
    """按点路径取 System 表的叶子值，缺失返回 None。"""
    node: Any = system
    for part in key.split('.'):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _flatten_keys(data: dict[str, Any], prefix: str = '') -> list[str]:
    """展平嵌套字典为全部点路径键（含中间节点，便于前缀判定）。"""
    keys: list[str] = []
    for key, value in data.items():
        path = f'{prefix}.{key}' if prefix else key
        keys.append(path)
        if isinstance(value, dict):
            keys.extend(_flatten_keys(value, path))
    return keys


def _strip_protected(override: dict[str, Any], system: dict[str, Any]) -> dict[str, Any]:
    """从覆盖数据中剔除 System 层已定义的键（递归），实现系统文案不可覆盖。"""
    result: dict[str, Any] = {}
    for key, value in override.items():
        system_value = system.get(key) if isinstance(system, dict) else None
        if isinstance(value, dict):
            nested = _strip_protected(value, system_value if isinstance(system_value, dict) else {})
            if nested:
                result[key] = nested
            continue
        if system_value is not None:
            continue
        result[key] = value
    return result


i18n = I18nManager()
