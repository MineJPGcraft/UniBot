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
SYSTEM_PATHS = {
    'zh': LOCALES_DIR / 'System.zh.toml',
    'en': LOCALES_DIR / 'System.en.toml',
}
MESSAGE_PATHS = {
    'zh': LOCALES_DIR / 'Messages.zh.toml',
    'en': LOCALES_DIR / 'Messages.en.toml',
}
LEGACY_MESSAGE_PATHS = {
    'zh': _ROOT / 'Config' / 'Messages.zh.toml',
    'en': _ROOT / 'Config' / 'Messages.en.toml',
}
MIGRATION_MARKER_PATH = _ROOT / 'Data' / '.locales_migrated'

# 支持语言（与 Core/I18n/Context.SUPPORTED_LANGUAGES 一致）
SUPPORTED_LANGUAGES = ('zh', 'en')

# System 层受保护键（系统指令 + 扩展/插件名称），用户改动一律忽略
_PROTECTED_PREFIXES = ('core.commands.bot', 'builtin')


def run_startup_migrations() -> None:
    """启动时执行全部幂等迁移，供 Bootstrap（Bot.py）调用。"""
    migrate_legacy_messages()


def migrate_legacy_messages() -> None:
    """
    把旧 `Config/Messages.*.toml` 的用户改动迁移到 `Core/Locales/Messages.*.toml`（幂等）。

    旧格式为「点路径表」（`[events]` / `[commands.*]` / `[builtin_extensions]` / `[plugins.*]`），
    迁移时折算为新命名空间键，只写入与当前默认层不同的**非系统**键，避免污染。
    迁移完成后写标记文件；无旧文件或已迁移时跳过。
    """
    if MIGRATION_MARKER_PATH.exists():
        return
    changed = False
    for language in SUPPORTED_LANGUAGES:
        legacy_path = LEGACY_MESSAGE_PATHS.get(language)
        if legacy_path is None or not legacy_path.exists():
            continue
        diff = _diff_legacy(language, _read_toml(legacy_path))
        if not diff:
            continue
        target_path = MESSAGE_PATHS.get(language)
        if target_path is None:
            continue
        merged = _deep_merge(_read_toml(target_path), diff)
        LOCALES_DIR.mkdir(parents=True, exist_ok=True)
        target_path.write_text(tomlkit.dumps(_to_tomlkit(merged)), encoding='Utf-8')
        changed = True
        print(f'[migrate] Merged legacy message overrides for [{language}] into Core/Locales/Messages.')
    MIGRATION_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_MARKER_PATH.write_text('migrated', encoding='Utf-8')
    if changed:
        print('[migrate] Legacy message migration done.')


# ===== 内部实现（纯文件级，不依赖 Core）=====


def _is_protected(path: str) -> bool:
    """判定点路径键是否属于 System 层（受保护，用户覆盖无效）。"""
    return any(path == prefix or path.startswith(f'{prefix}.') for prefix in _PROTECTED_PREFIXES)


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(tomlkit.parse(path.read_text('Utf-8')).unwrap())


def _default_keys(language: str) -> dict[str, Any]:
    """读取 System + Messages 默认层，展平为「点路径 → 叶子值」（替代 i18n.available_keys）。"""
    known: dict[str, Any] = {}
    for path in (SYSTEM_PATHS.get(language), MESSAGE_PATHS.get(language)):
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
    diff: dict[str, Any] = {}
    for namespace, table in (('core', legacy_core), ('builtin', legacy_builtin)):
        for path, value in _flatten_named(namespace, table).items():
            if _is_protected(path):
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


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
            continue
        result[key] = value
    return result


def _to_tomlkit(data: dict[str, Any]) -> tomlkit.TOMLDocument:
    """把嵌套命名空间字典转换为 tomlkit 文档（顶层为超表，输出分段表）。"""
    document = tomlkit.document()
    document.add(tomlkit.comment('机器人消息文案：可自由修改，保存后热生效（系统键写入将被忽略）。'))
    for namespace, table in data.items():
        if not isinstance(table, dict):
            continue
        node = tomlkit.table(is_super_table=True)
        for key, value in table.items():
            section = tomlkit.table()
            _fill_section(section, value if isinstance(value, dict) else {'value': value})
            node[key] = section
        document[namespace] = node
    return document


def _fill_section(section: Any, data: dict[str, Any]) -> None:
    for key, value in data.items():
        if isinstance(value, dict):
            sub = tomlkit.table()
            _fill_section(sub, value)
            section[key] = sub
        elif isinstance(value, list):
            section[key] = value
        else:
            section[key] = value


def main() -> int:
    """命令行入口：在 UniBot 目录执行 `python Scripts/migrate_messages.py`。"""
    run_startup_migrations()
    return 0


if __name__ == '__main__':
    sys.exit(main())
