"""
扩展 Python 依赖聚合：扫描已启用扩展清单，同步到 pyproject.toml 的 extensions 组。

扩展通过 `Extension.toml` 的 `[dependencies].python` 声明第三方 Python 库。
本模块把**已启用**扩展的依赖聚合去重，合并写入 `pyproject.toml` 的
`[project.optional-dependencies].extensions` 组，供 `uv sync --extra extensions`
统一安装。已写入的既有依赖会保留：未启用或卸载的扩展不会自动移除已有条目，
避免误删用户环境中已安装的包。
"""

import tomllib
from collections.abc import Mapping
from pathlib import Path

import tomlkit

from Scripts.Constants import CONFIG_EXTENSIONS_FILE, EXTENSIONS_DIR, MANIFEST_FILE, PYPROJECT_PATH
from Scripts.Logging import logger

# 收集所有扩展依赖的 optional-dependencies 组名
EXTENSIONS_EXTRA = 'extensions'


def load_enabled_config() -> dict:
    """读取扩展启停配置文件，缺失或损坏时返回空 dict（视为全部启用）。"""
    try:
        return tomlkit.parse(CONFIG_EXTENSIONS_FILE.read_text('Utf-8'))
    except Exception as error:
        logger.warning(f'Failed to read extension enable/disable config: {error}, defaulting to all enabled.')
        return {}


def is_extension_enabled(enabled_config: Mapping, extension_id: str) -> bool:
    """从启停配置中读取单个扩展的启用标志，缺失时默认启用。"""
    return bool(enabled_config.get(extension_id, {}).get('enabled', True))


def _is_enabled(extension_id: str) -> bool:
    """读取 Config/Extensions.toml 中扩展的启停标志，缺失时默认启用。"""
    return is_extension_enabled(load_enabled_config(), extension_id)


def _read_extension_dependencies(manifest_path: Path) -> list[str]:
    """读取单个扩展清单中的 [dependencies].python 依赖列表。"""
    try:
        data = tomllib.loads(manifest_path.read_text('Utf-8'))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    dependencies = data.get('dependencies', {})
    python = dependencies.get('python', [])
    return list(python) if isinstance(python, list) else []


def collect_extension_dependencies() -> list[str]:
    """扫描 Extensions/ 下所有**已启用**扩展目录，聚合去重所有 Python 依赖。"""
    if not EXTENSIONS_DIR.exists():
        return []
    collected: list[str] = []
    seen: set[str] = set()
    for entry in EXTENSIONS_DIR.iterdir():
        if not entry.is_dir() or entry.name.startswith(('.', '_')):
            continue
        # 未启用的扩展不参与依赖收集（其已写入的依赖也不会被移除）
        if not _is_enabled(entry.name):
            continue
        manifest_path = entry / MANIFEST_FILE
        if not manifest_path.exists():
            continue
        for dependency in _read_extension_dependencies(manifest_path):
            if dependency not in seen:
                seen.add(dependency)
                collected.append(dependency)
    return collected


def sync_extension_dependencies(remove: list[str] | None = None) -> None:
    """
    把已启用扩展收集到的依赖合并写入 pyproject.toml 的 extensions 组。

    默认只增不删：保留组内已有的依赖条目，仅追加新收集到的依赖。这样未启用
    扩展的依赖不会新增，而已写入的依赖（可能已被手动安装）也不会被移除。

    remove：需要尝试移除的依赖清单（通常为被卸载扩展声明的依赖）。仅当某个
    依赖同时满足「在被移除清单中」且「不再被任何已启用扩展声明」时才会被移除，
    避免误删其它扩展仍在使用的共享依赖。
    """
    if not PYPROJECT_PATH.exists():
        return
    body = tomlkit.parse(PYPROJECT_PATH.read_text('Utf-8'))
    project = body.setdefault('project', {})
    optional = project.setdefault('optional-dependencies', {})
    existing = list(optional.get(EXTENSIONS_EXTRA, []))
    current = collect_extension_dependencies()
    current_set = set(current)
    remove_set = set(remove or [])
    # 保留：不在移除清单中的依赖，或仍在当前已启用扩展集合中的共享依赖
    merged = [dep for dep in existing if dep not in remove_set or dep in current_set]
    seen: set[str] = set(merged)
    for dependency in current:
        if dependency not in seen:
            seen.add(dependency)
            merged.append(dependency)
    optional[EXTENSIONS_EXTRA] = merged
    PYPROJECT_PATH.write_text(tomlkit.dumps(body), encoding='Utf-8')
