"""I18n 管理器：默认语言包 + 用户逐键覆盖、扁平点路径表查找，以及按来源选语言的上下文。

两层模型（Refactor §5）：
- **默认层**：System 层（`Core/Locales/System.*.toml`：系统指令 `/bot`、内置扩展/插件名称、
  面板界面 `api.*`）与 Messages 层（`Core/Locales/Messages.*.toml`：事件播报、其余指令）
  以及扩展语言包（`Extensions/<id>/Locales/*`：`ext.<id>.*`），均为**默认值**来源。
- **覆盖层**（用户 `Config/Messages.{zh,en}.toml`，可编辑）：**只保存用户改过的键**。

**可覆盖性与语言选择均以文件来源判定**（同一份 `is_system_key` 依据）：
- System 文件注册的键**受保护**（用户覆盖被忽略）且跟随**系统语言**（WebUI 每请求
  `Accept-Language`）；未显式设置系统语言时（QQ 等机器人场景）回退**消息语言**；
- Messages 文件与扩展语言包注册的键**可被用户覆盖**且跟随**消息语言**（`Config.toml` 的
  `language`）——注意同一 `core.*` / `ext.*` 命名空间在 System 与 Messages 中均可能出现，
  因此判定按「该键是否由 System 文件提供」而非命名空间前缀。

各层注册时统一展平为「点路径 → 叶子值」扁平表，合并即按优先级 `update`、查找即 `dict.get`。
系统语言与消息语言各由独立 ContextVar 承载（见本模块顶部），**不再按命名空间路由**。
"""

from __future__ import annotations

from contextvars import ContextVar
from string import Formatter
from typing import Any

from Core.Logging import logger

# 支持的语言与默认语言
SUPPORTED_LANGUAGES: tuple[str, ...] = ('zh', 'en')
DEFAULT_LANGUAGE = 'zh'

# 系统语言（WebUI 界面 / 系统键文案）：中间件按每请求 Accept-Language 设置；
# 未显式设置时（QQ 等机器人场景）由 get_system_locale 回退消息语言。
_system_language: ContextVar[str | None] = ContextVar('system_language', default=None)
# 消息语言（机器人消息）：启动时按 Config.toml 的 language 对齐
_messages_language: ContextVar[str] = ContextVar('messages_language', default=DEFAULT_LANGUAGE)


def _normalize(language: str) -> str:
    """未支持的语言回退默认语言。"""
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_system_locale() -> str:
    """获取当前上下文的系统语言；未显式设置时回退消息语言（QQ 场景与机器人消息保持一致）。"""
    return _system_language.get() or _messages_language.get()


def set_system_locale(language: str) -> None:
    """设置当前上下文的系统语言（WebUI 界面语言），未支持的语言回退默认语言。"""
    _system_language.set(_normalize(language))


def get_messages_locale() -> str:
    """获取当前上下文的消息语言（机器人对外文案语言）。"""
    return _messages_language.get()


def set_messages_locale(language: str) -> None:
    """设置当前上下文的消息语言（机器人对外文案语言），未支持的语言回退默认语言。"""
    _messages_language.set(_normalize(language))


def normalize_language(accept_language: str | None) -> str:
    """从 Accept-Language 头解析语言（如 zh-CN → zh），无法识别时回退默认语言。"""
    for part in (accept_language or '').split(','):
        tag = part.split(';')[0].strip().lower()
        language = next((item for item in SUPPORTED_LANGUAGES if tag.startswith(item)), None)
        if language is not None:
            return language
    return DEFAULT_LANGUAGE


class I18nManager:
    """默认语言包与用户逐键覆盖的注册、合并、查找与渲染编排。"""

    def __init__(self) -> None:
        # 各层均为「语言 -> 扁平点路径表」（叶子值为 str 或 list[str]）
        # System 层：系统自带，受保护不可被覆盖
        self._system: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # Messages 层：机器人消息默认文案
        self._messages: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 扩展语言包：语言 -> {命名空间: 扁平表}（`ext.<id>`）
        self._extensions: dict[str, dict[str, dict[str, Any]]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 覆盖层：用户编辑（仅存改过的键）；与 System 键同名者在合并时被忽略
        self._override: dict[str, dict[str, Any]] = {language: {} for language in SUPPORTED_LANGUAGES}
        # 生效目录：语言 -> 合并后的扁平表（System → Messages → 扩展 → 覆盖层）
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
        """重建生效目录：System → Messages → 扩展 → 覆盖层；System 文件提供的键不可被覆盖。"""
        for language in SUPPORTED_LANGUAGES:
            merged = dict(self._system[language])
            system_keys = tuple(self._system[language])
            for source in (self._messages[language], *self._extensions[language].values(), self._override[language]):
                for key, value in source.items():
                    if key not in system_keys:
                        merged[key] = value
            self._catalog[language] = merged

    # ===== 覆盖层 =====

    def load_override(self, language: str, data: dict[str, Any]) -> None:
        """加载用户覆盖层（`Config/Messages.<language>.toml` 解析结果），System 键被剔除。"""
        if language not in SUPPORTED_LANGUAGES:
            return
        self._override[language] = _flatten(data)
        self._rebuild()

    # ===== 查询 / 渲染 =====

    def render(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        """按点路径取值并格式化占位符；`locale` 为空时按键来源选语言，键缺失返回原文并告警。"""
        language = self.resolve_locale(key, locale)
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
        """按点路径取原始叶子值（字符串或字符串列表）；`locale` 为空时按键来源选语言。"""
        language = self.resolve_locale(key, locale)
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
        """判断点路径键是否受保护（由 System 文件提供，用户覆盖无效）。"""
        return self.is_system_key(key)

    def is_system_key(self, key: str) -> bool:
        """判断点路径键是否由 System 文件提供（决定其受保护性与语言来源）。"""
        return any(key in self._system[language] for language in SUPPORTED_LANGUAGES)

    def resolve_locale(self, key: str, locale: str | None = None) -> str:
        """
        选择渲染语言：显式 `locale` 优先（非法值回退默认语言）；否则按键来源——
        System 文件键用系统语言（未显式设置时回退消息语言），Messages／扩展键用消息语言。
        """
        if locale is not None:
            return _normalize(locale)
        if self.is_system_key(key):
            return get_system_locale()
        return get_messages_locale()

    # ===== 目录访问（供 WebUI 消息编辑器构建树 / 校验）=====

    def catalog_keys(self, language: str, prefix: str | None = None) -> list[str]:
        """返回生效目录的点路径键列表，可按命名空间前缀过滤（如 `core.commands.`）。"""
        target = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        keys = self._catalog[target].keys()
        if prefix is None:
            return list(keys)
        return [key for key in keys if key.startswith(prefix)]

    def raw_value(self, language: str, key: str) -> Any:
        """按语言取生效目录的原始叶子值（str 或 list），缺失返回 None。"""
        target = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        return self._catalog[target].get(key)

    def base_value(self, language: str, key: str) -> Any:
        """按语言取**未叠加用户覆盖**的默认叶子值（System → Messages → 扩展），缺失返回 None。"""
        target = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        if key in self._system[target]:
            return self._system[target][key]
        if key in self._messages[target]:
            return self._messages[target][key]
        for table in self._extensions[target].values():
            if key in table:
                return table[key]
        return None

    def find_placeholders(self, template: str) -> list[str]:
        """解析模板中的命名占位符（`{name}`），按首次出现去重，供前端插入参考。"""
        names: list[str] = []
        formatter = Formatter()
        for _, field_name, _, _ in formatter.parse(template):
            if field_name is None or field_name in names:
                continue
            names.append(field_name)
        return names


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
