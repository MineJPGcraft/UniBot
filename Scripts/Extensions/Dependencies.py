"""
扩展 Python 依赖聚合与安装：以 uv 命令为唯一写入通道，同步扩展声明的第三方库。

扩展通过 `Extension.toml` 的 `[dependencies].python` 声明第三方 Python 库。
本模块把**已启用**扩展的依赖聚合去重，写入 `pyproject.toml` 的
`[project.optional-dependencies].extensions` 组（该组由框架独占维护）。

写入一律通过 `uv add --optional extensions` / `uv remove --optional extensions`
完成，不再手工拼接 pyproject.toml 文本，避免格式漂移与锁文件不同步。
`extensions` 组由框架独占：组内已无扩展声明（且未被保护）的条目会被 `uv remove`
清理；其它 extra（如 webui）的依赖不受影响（`uv sync --inexact`）。
"""

from __future__ import annotations

import asyncio
import tempfile
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path

import tomlkit

from Scripts.Constants import CONFIG_EXTENSIONS_FILE, CONFIG_TOML_PATH, EXTENSIONS_DIR, MANIFEST_FILE, PYPROJECT_PATH
from Scripts.Logging import logger

# 收集所有扩展依赖的 optional-dependencies 组名（框架独占维护，勿手动编辑）
EXTENSIONS_EXTRA = 'extensions'

# 影响 uv sync 结果的可选功能开关（Config.toml 段落 + 字段 → extra 名）
EXTRA_CONFIG_FIELDS = {
    'webui': ('webui', 'enabled'),
}

# uv 单次命令超时（秒），避免网络异常时任务长期挂起
UV_COMMAND_TIMEOUT = 900

# 逐行日志回调（任务中心注入；缺省只写应用日志）
LogSink = Callable[[str], None]


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


def read_extra_dependencies(extra: str = EXTENSIONS_EXTRA) -> list[str]:
    """读取 pyproject.toml 中指定 optional-dependencies 组的现有条目。"""
    if not PYPROJECT_PATH.exists():
        return []
    try:
        data = tomlkit.parse(PYPROJECT_PATH.read_text('Utf-8'))
    except Exception as error:
        logger.warning(f'Failed to read pyproject.toml: {error}')
        return []
    extra_dependencies = data.get('project', {}).get('optional-dependencies', {}).get(extra, [])
    return [str(item) for item in extra_dependencies]


def package_name(dependency: str) -> str:
    """从依赖声明中提取包名（去除 extras 与版本约束）。"""
    for separator in ('[', '>', '<', '~', '!', '=', ';', ' '):
        if separator in dependency:
            dependency = dependency.split(separator, 1)[0]
    return dependency.strip()


def plan_extension_dependency_changes() -> tuple[list[str], list[str]]:
    """
    计算 extensions 组的增删计划，返回 (需新增的声明, 需移除的包名)。

    组内当前无任何已启用扩展声明的条目会被移除（该组由框架独占维护，
    因此不做「只增不删」保护）；未启用扩展的依赖同样不参与保留集合。
    """
    desired = collect_extension_dependencies()
    existing = read_extra_dependencies()
    desired_names = {package_name(item) for item in desired}
    existing_names = {package_name(item) for item in existing}
    to_add = [item for item in desired if package_name(item) not in existing_names]
    to_remove = sorted(name for name in existing_names if name not in desired_names)
    return to_add, to_remove


def get_enabled_extras() -> list[str]:
    """获取当前配置中已启用的可选功能（从 Config.toml 读取）。"""
    try:
        config = tomllib.loads(CONFIG_TOML_PATH.read_text('Utf-8'))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    return [
        extra
        for extra, (section, field) in EXTRA_CONFIG_FIELDS.items()
        if config.get(section, {}).get(field, False)
    ]


# ===== uv 命令构造与执行 =====


def build_uv_add_command(packages: list[str], extra: str = EXTENSIONS_EXTRA) -> list[str]:
    """构造向指定 extra 追加依赖的 uv 命令（--no-sync，由调用方统一同步）。"""
    return ['uv', 'add', '--optional', extra, '--no-sync', *packages]


def build_uv_remove_command(packages: list[str], extra: str = EXTENSIONS_EXTRA) -> list[str]:
    """构造从指定 extra 移除依赖的 uv 命令（--no-sync，由调用方统一同步）。"""
    return ['uv', 'remove', '--optional', extra, '--no-sync', *packages]


def build_uv_add_main_command(packages: list[str]) -> list[str]:
    """构造向 project.dependencies 追加依赖的 uv 命令（--no-sync，由调用方统一同步）。"""
    return ['uv', 'add', '--no-sync', *packages]


def build_uv_remove_main_command(packages: list[str]) -> list[str]:
    """构造从 project.dependencies 移除依赖的 uv 命令（--no-sync，由调用方统一同步）。"""
    return ['uv', 'remove', '--no-sync', *packages]


def build_uv_sync_command() -> list[str]:
    """
    构造 uv sync 命令：带上全部已启用的 extras，并加 --inexact。

    --inexact 是关键：uv sync 默认会把环境同步到「仅含选中组」的快照状态，
    单 extra 会卸载其它组已安装的包（如 webui 的 psutil）；加 --inexact 后
    只安装缺失项，不卸载多余项。
    """
    command = ['uv', 'sync', '--inexact']
    for extra in get_enabled_extras():
        command.extend(('--extra', extra))
    # 扩展依赖统一收口到 extensions 可选组
    command.extend(('--extra', EXTENSIONS_EXTRA))
    return command


async def run_uv_command(command: list[str], log: LogSink | None = None, timeout: float = UV_COMMAND_TIMEOUT) -> None:
    """
    执行 uv 命令并逐行回报输出，非零退出码抛 RuntimeError。

    输出重定向到临时文件而非管道：uv 的进度条会写大量控制字符，管道缓冲区
    写满后子进程会阻塞，导致 wait() 永久挂起。
    """
    logger.info(f'Running uv command: {" ".join(command)}')
    if log is not None:
        log(f'$ {" ".join(command)}')
    with tempfile.TemporaryFile(mode='w+b') as output_file:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=output_file,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            exit_code = await asyncio.wait_for(process.wait(), timeout=timeout)
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise RuntimeError(f'uv command timed out after {timeout}s: {" ".join(command)}') from error
        output_file.seek(0)
        content = output_file.read().decode('Utf-8', errors='replace')
    for line in content.splitlines():
        stripped = line.rstrip()
        if stripped and log is not None:
            log(stripped)
    if exit_code != 0:
        raise RuntimeError(f'uv command failed with exit code {exit_code}: {" ".join(command)}')


async def apply_dependency_changes(
    to_add: list[str],
    to_remove: list[str] | None = None,
    log: LogSink | None = None,
) -> None:
    """把指定依赖写入/移出 extensions 组并同步环境（供插件、驱动等复用）。"""
    if to_remove:
        await run_uv_command(build_uv_remove_command(to_remove), log)
    if to_add:
        await run_uv_command(build_uv_add_command(to_add), log)
    await run_uv_command(build_uv_sync_command(), log)


async def apply_main_dependency_changes(
    to_add: list[str],
    to_remove: list[str] | None = None,
    log: LogSink | None = None,
) -> None:
    """
    把指定依赖写入/移出 project.dependencies（主依赖组）并同步环境。

    适配器驱动（httpx / websockets 等）与 NoneBot 插件包都落在主依赖组，
    统一走 `uv add` / `uv remove` 以免手工改写 pyproject.toml。
    """
    if to_remove:
        await run_uv_command(build_uv_remove_main_command(to_remove), log)
    if to_add:
        await run_uv_command(build_uv_add_main_command(to_add), log)
    await run_uv_command(build_uv_sync_command(), log)


async def sync_extension_dependencies(log: LogSink | None = None) -> None:
    """
    按当前扩展声明同步 extensions 组并执行 uv sync（异步，供任务中心调用）。

    流程：计划增删 → `uv remove` → `uv add`（均 --no-sync）→ `uv sync --inexact`。
    组内无变化时仍执行一次 uv sync，保证环境与声明一致。
    """
    if log is not None:
        log('Collecting Python dependencies declared by enabled extensions...')
    to_add, to_remove = plan_extension_dependency_changes()
    if not to_add and not to_remove and log is not None:
        log('Extension dependency declarations are up to date.')
    await apply_dependency_changes(to_add, to_remove, log)
