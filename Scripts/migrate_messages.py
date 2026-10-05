"""
存量数据迁移脚本（**完全独立**，零 Core 依赖）。

设计约束（Refactor §5.9）：
- 本脚本不 import 任何 `Core.*` 模块，可脱离机器人进程单独运行：
      在 UniBot 目录执行  `python Scripts/migrate_messages.py`
- 迁移逻辑只做**文件级读写**（旧消息包 → 新 `Core/Locales/Messages.*.toml`），
  自带路径常量与「系统受保护键」判定，不依赖运行中的 I18n 引擎。
- Bot 启动时通过 `from Scripts.migrate_messages import run_startup_migrations`
  调用（见 Bot.py），保证迁移与业务代码解耦。

当前迁移：
- `migrate_legacy_messages`：把旧 `Config/Messages.{zh,en}.toml`（旧点路径格式）中与
  默认消息层不同的用户改动并入 `Core/Locales/Messages.{zh,en}.toml`（System 键被忽略，幂等）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import tomlkit

# ===== 自带路径常量（与 Core/Constants.py 保持一致，但不依赖它）=====
# 脚本位于 UniBot/Scripts/，项目根为其父目录
_ROOT = Path(__file__).resolve().parent.parent
LOCALES_DIR = _ROOT / 'Core' / 'Locales'
CONFIG_DIR = _ROOT / 'Config'
SYSTEM_PATHS = {
    'zh': LOCALES_DIR / 'System.zh.toml',
    'en': LOCALES_DIR / 'System.en.toml',
}
# 默认机器人消息层（Core/Locales，随核心分发）与用户覆盖层（Config/，仅存改动键）
DEFAULT_MESSAGE_PATHS = {
    'zh': LOCALES_DIR / 'Messages.zh.toml',
    'en': LOCALES_DIR / 'Messages.en.toml',
}
OVERRIDE_MESSAGE_PATHS = {
    'zh': CONFIG_DIR / 'Messages.zh.toml',
    'en': CONFIG_DIR / 'Messages.en.toml',
}
# 旧消息包与新版覆盖层同路径（旧格式 → 新格式的一次性转换）
LEGACY_MESSAGE_PATHS = dict(OVERRIDE_MESSAGE_PATHS)
MIGRATION_MARKER_PATH = _ROOT / 'Data' / '.locales_migrated'

# 支持语言（与 Core/I18n/Engine/Context.SUPPORTED_LANGUAGES 一致）
SUPPORTED_LANGUAGES = ('zh', 'en')


def run_startup_migrations() -> None:
    """启动时执行全部幂等迁移，供 Bootstrap（Bot.py）调用。"""
    migrate_legacy_messages()


def migrate_legacy_messages() -> None:
    """
    把旧 `Config/Messages.*.toml` 的用户改动转换为新覆盖层格式（幂等）。

    旧格式为「点路径表」（`[events]` / `[commands.*]` / `[builtin_extensions]` / `[plugins.*]`）；
    新格式为「默认键命名空间 + **仅存用户改动键**」。迁移时把旧表折算为新命名空间键，
    只保留与当前默认层不同、且非系统保护的键，整文件重写为新格式。
    迁移完成后写标记文件；无旧文件或已迁移时跳过。
    """
    if MIGRATION_MARKER_PATH.exists():
        return
    changed = False
    for language in SUPPORTED_LANGUAGES:
        legacy_path = LEGACY_MESSAGE_PATHS.get(language)
        if legacy_path is None or not legacy_path.exists():
            continue
        legacy = _read_toml(legacy_path)
        # 已是新格式（顶层含命名空间表）则不转换，仅确保标记写盘
        if _looks_like_new_format(legacy):
            changed = True
            continue
        diff = _diff_legacy(language, legacy)
        target_path = OVERRIDE_MESSAGE_PATHS.get(language)
        if target_path is None:
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(_render_override(diff), encoding='Utf-8')
        changed = True
        print(f'[migrate] Converted legacy message overrides for [{language}] into Config/Messages.')
    MIGRATION_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_MARKER_PATH.write_text('migrated', encoding='Utf-8')
    if changed:
        print('[migrate] Legacy message migration done.')


def _looks_like_new_format(raw: dict[str, Any]) -> bool:
    """粗判文件是否已是新覆盖层格式（顶层为 `core` / `api` / `ext` 等命名空间表）。"""
    namespaces = {'core', 'api', 'ext'}
    return any(key in namespaces and isinstance(value, dict) for key, value in raw.items())


def _render_override(data: dict[str, Any]) -> str:
    """把嵌套命名空间字典渲染为新覆盖层 TOML 文本。"""
    header = '# 仅保存你在 WebUI 中修改过的消息键；可覆盖默认语言包中的任意文案（系统键：系统指令、内置扩展/插件名称、面板界面文案除外）。'
    if not data:
        return f'{header}\n'
    return f'{header}\n\n{tomlkit.dumps(data)}'


# ===== 内部实现（纯文件级，不依赖 Core）=====


def _system_keys(language: str) -> set[str]:
    """读取 System 文件并展平为点路径键集合（系统键：用户覆盖无效）。"""
    path = SYSTEM_PATHS.get(language)
    if path is None or not path.exists():
        return set()
    return set(_flatten_namespace(_read_toml(path)))


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(tomlkit.parse(path.read_text('Utf-8')).unwrap())


def _default_keys(language: str) -> dict[str, Any]:
    """读取 System + 默认 Messages 层，展平为「点路径 → 叶子值」（供迁移比对）。"""
    known: dict[str, Any] = {}
    for path in (SYSTEM_PATHS.get(language), DEFAULT_MESSAGE_PATHS.get(language)):
        if path is None or not path.exists():
            continue
        known.update(_flatten_namespace(_read_toml(path)))
    return known


def _flatten_namespace(data: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    """展平已含命名空间前缀的嵌套表为「点路径 → 值」（仅叶子：字符串 / 列表）。"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_namespace(value, path))
        elif isinstance(value, (str, list)):
            result[path] = value
    return result


def _diff_legacy(language: str, legacy: dict[str, Any]) -> dict[str, Any]:
    """把旧消息包折算成命名空间键，并剔除与默认层相同或受系统保护的项。"""
    legacy_core, legacy_builtin = _split_legacy(legacy)
    known = _default_keys(language)
    system_keys = _system_keys(language)
    diff: dict[str, Any] = {}
    for namespace, table in (('core', legacy_core), ('builtin', legacy_builtin)):
        for path, value in _flatten_named(namespace, table).items():
            if path in system_keys:
                continue
            if known.get(path) != value:
                _assign(diff, path, value)
    return diff


def _split_legacy(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """拆分旧消息包为 (core 表, builtin 表)。"""
    core: dict[str, Any] = {}
    builtin: dict[str, Any] = {}
    for key, value in raw.items():
        if key == 'builtin_extensions' and isinstance(value, dict):
            for extension_id, display_name in value.items():
                builtin.setdefault(extension_id, {})['name'] = display_name
            continue
        if key == 'plugins' and isinstance(value, dict):
            for plugin_id, table in value.items():
                builtin.setdefault(plugin_id, {}).update(table)
            continue
        core[key] = value
    return core, builtin


def _flatten_named(namespace: str, table: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    """展平命名空间表为「点路径 → 值」映射（含命名空间前缀）。"""
    result: dict[str, Any] = {}
    for key, value in table.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_named(namespace, value, path))
        elif isinstance(value, (str, list)):
            result[f'{namespace}.{path}'] = value
    return result


def _assign(table: dict[str, Any], dotted: str, value: Any) -> None:
    """按点路径写入嵌套字典。"""
    node = table
    parts = dotted.split('.')
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def main() -> int:
    """命令行入口：在 UniBot 目录执行 `python Scripts/migrate_messages.py`。"""
    run_startup_migrations()
    return 0


if __name__ == '__main__':
    sys.exit(main())
