"""
语言包加载（Infrastructure 层）：读取磁盘上的语言包并注册进 I18n 引擎。

引擎（Core/I18n）自身不读写磁盘；本模块负责：
- 系统层：`Core/Locales/System.{zh,en}.toml`（只读，系统指令与扩展/插件名称）→ `core.commands.bot` / `builtin.*`
- 消息层：`Core/Locales/Messages.{zh,en}.toml`（用户可改）→ `core.events` / `core.commands.*` / `api.*`
- 覆盖层：`Core/Locales/Messages.{zh,en}.toml` 中用户改写的键（与消息层同文件，System 键被忽略）
- 扩展语言包：`Extensions/<id>/Locales/{zh,en}.toml` → `ext.<id>.*`

热切换语言或保存消息文案后重新调用 `register_all()` 即可（引擎整体重建）。
System 与 Messages 使用同一份磁盘文件（`Core/Locales/Messages.<lang>.toml`）：其中 `core.commands.bot`
与 `builtin.*` 为系统键（写入被忽略），其余为用户可改键。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomlkit

from Core.Config import config
from Core.Constants import MESSAGE_PATHS, SYSTEM_PATHS
from Core.I18n import i18n
from Core.I18n.Context import SUPPORTED_LANGUAGES, set_locale
from Core.Logging import logger


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(tomlkit.parse(path.read_text('Utf-8')).unwrap())


def register_all() -> None:
    """加载并注册全部语言包（System 层 + Messages 层 + 覆盖层），供 Bootstrap 启动时调用。"""
    _load_system()
    _load_messages()
    _sync_locale()


def _load_system() -> None:
    """读取 `Core/Locales/System.*.toml` 并注册进引擎（System 层：系统指令 + 扩展/插件名称）。"""
    tables = {language: _read_toml(SYSTEM_PATHS[language]) for language in SUPPORTED_LANGUAGES}
    i18n.register_system(tables)


def _load_messages() -> None:
    """读取 `Core/Locales/Messages.*.toml` 并注册进引擎（默认消息层），随后作为用户覆盖层加载。"""
    tables = {language: _read_toml(MESSAGE_PATHS[language]) for language in SUPPORTED_LANGUAGES}
    i18n.register_messages(tables)
    for language in SUPPORTED_LANGUAGES:
        path = MESSAGE_PATHS[language]
        if not path.exists():
            continue
        i18n.load_override(language, tables[language], path.read_text('Utf-8'))


def _sync_locale() -> None:
    """把当前语言上下文对齐 Config.toml 的 language 字段。"""
    set_locale(config.language)


def read_override(language: str) -> str:
    """读取用户可改语言包原始文本（供 WebUI 消息编辑器展示）。"""
    path = MESSAGE_PATHS.get(language, MESSAGE_PATHS['zh'])
    return path.read_text('Utf-8') if path.exists() else ''


def write_override(language: str, content: str) -> None:
    """校验并写回用户语言包，写盘后热重载全部语言包（System 键由引擎忽略）。"""
    path = MESSAGE_PATHS.get(language, MESSAGE_PATHS['zh'])
    tomlkit.parse(content)
    path.write_text(content, encoding='Utf-8')
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
