"""
语言包加载（Infrastructure 层）：读取磁盘上的默认语言包与用户覆盖层并注册进 I18n 引擎。

引擎（`Core/I18n/Engine`）自身不读写磁盘；本模块负责：
- 默认层：`Core/Locales/System.{zh,en}.toml`（系统指令 + 扩展/插件名称 + 面板界面 `api.*`）
  与 `Core/Locales/Messages.{zh,en}.toml`（机器人消息默认文案 + 扩展消息）；
- 覆盖层：`Config/Messages.{zh,en}.toml`（**仅保存用户改过的键**，可覆盖除系统键
  （系统指令、内置扩展/插件名称、`api.*` 界面文案）外的任意文案，含 `ext.*` 扩展消息）；
- 扩展语言包：`Extensions/<id>/Locales/{zh,en}.toml` → `ext.<id>.*`。

热切换语言或保存消息文案后重新调用 `register_all()` 即可（引擎整体重建）。
`register_all()` 末尾把**消息语言**对齐 `Config.toml` 的 `language`（System 文件键的系统语言
由 WebUI 每请求 `Accept-Language` 单独控制，见 `Core/Web/Locale.py`）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomlkit

from Core.Config import config
from Core.Constants import MESSAGE_PATHS, OVERRIDE_MESSAGE_PATHS, SYSTEM_PATHS
from Core.Logging import logger

from .Engine import SUPPORTED_LANGUAGES, i18n, set_messages_locale

_OVERRIDE_HEADER = '# 仅保存你在 WebUI 中修改过的消息键；可覆盖默认语言包中的任意文案（系统键：系统指令、内置扩展/插件名称、面板界面文案除外）。'


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(tomlkit.parse(path.read_text('Utf-8')).unwrap())


def overrides_path(language: str) -> Path:
    """返回某语言的用户覆盖层文件路径（`Config/Messages.<language>.toml`）。"""
    return OVERRIDE_MESSAGE_PATHS.get(language, OVERRIDE_MESSAGE_PATHS['zh'])


def read_override(language: str) -> dict[str, Any]:
    """读取某语言的用户覆盖层原始嵌套字典（缺失返回空字典）。"""
    return _read_toml(overrides_path(language))


def register_all() -> None:
    """加载并注册全部语言包（默认层 + 用户覆盖层），供 Bootstrap 启动时调用。"""
    _load_system()
    _load_messages()
    _load_override()
    _sync_locale()


def _load_system() -> None:
    """读取 `Core/Locales/System.*.toml` 并注册进引擎（系统指令 + 扩展/插件名称 + api.*）。"""
    tables = {language: _read_toml(SYSTEM_PATHS[language]) for language in SUPPORTED_LANGUAGES}
    i18n.register_system(tables)


def _load_messages() -> None:
    """读取 `Core/Locales/Messages.*.toml` 并注册进引擎（机器人消息与扩展文案默认层）。"""
    tables = {language: _read_toml(MESSAGE_PATHS[language]) for language in SUPPORTED_LANGUAGES}
    i18n.register_messages(tables)


def _load_override() -> None:
    """读取 `Config/Messages.*.toml` 并作为用户覆盖层加载（受保护键由引擎剔除）。"""
    for language in SUPPORTED_LANGUAGES:
        i18n.load_override(language, read_override(language))


def _sync_locale() -> None:
    """把当前消息语言上下文对齐 Config.toml 的 language 字段（界面语言不受影响）。"""
    set_messages_locale(config.language)


def write_override(language: str, data: dict[str, Any]) -> None:
    """以结构化字典写回用户覆盖层（仅存改动键），写盘后热重载全部语言包。"""
    path = overrides_path(language)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = tomlkit.dumps(_prune(data)) if data else ''
    path.write_text(f'{_OVERRIDE_HEADER}\n\n{body}', encoding='Utf-8')
    register_all()
    logger.success('Message texts saved and reloaded.')


def register_extension_locales(extension_id: str, locales_dir: Path) -> None:
    """
    注册扩展语言包 `Extensions/<id>/Locales/{zh,en}.toml` → `ext.<id>.*`。

    扩展无需写代码即可携带翻译；卸载/热重载时由 `unregister_extension_locales` 注销后重新注册。
    """
    tables: dict[str, dict[str, Any]] = {}
    for language in SUPPORTED_LANGUAGES:
        tables[language] = _read_toml(locales_dir / f'{language}.toml')
    if any(tables.values()):
        i18n.register_extension(f'ext.{extension_id}', tables)
        logger.debug(f'Registered i18n locales for extension {extension_id}.')


def unregister_extension_locales(extension_id: str) -> None:
    """注销某扩展的语言包，避免热重载后残留旧文案。"""
    i18n.unregister_extension(f'ext.{extension_id}')


def _prune(data: dict[str, Any]) -> dict[str, Any]:
    """剔除空字典分支，只保留有叶子值的键。"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            nested = _prune(value)
            if nested:
                result[key] = nested
            continue
        result[key] = value
    return result
