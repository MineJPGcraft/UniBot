"""扩展市场管理器：注册表缓存、安装状态持久化与安全安装/卸载事务。

市场扩展从 GitHub Release 以源码 zip 分发。安装流程：
下载 → SHA-256 校验 → 安全解压 → 清单校验 → 临时目录原子替换。
任一步失败都不得改变当前扩展版本（可回滚事务）。
安装状态统一写入 `Data/Extension/States.toml`。

不指定版本时自动挑选**兼容当前 UniBot 版本**的最新发布：
兼容版本存在则直接安装；若该扩展仅有不兼容的新版本，则回退到最新的历史兼容版本；
一个兼容版本都没有时拒绝安装并提示此扩展不支持当前核心版本。
"""

import asyncio
import hashlib
import shutil
import tempfile
import time
from pathlib import Path

import tomlkit

from Core.Constants import MARKET_CACHE_TTL, STATES_PATH
from Core.Files import atomic_write
from Core.Logging import exception_logger, logger
from Core.Network import github_download, request
from Core.Utils import ArchiveError, safe_extract_zip

from ..Errors import ExtensionError, ManifestError
from ..Manifest import (
    ExtensionManifest,
    get_unibot_version,
    is_unibot_compatible,
    parse_manifest,
    validate_unibot_constraint,
)
from ..Runtime.Loader import EXTENSIONS_DIR
from ..Runtime.Manager import extension_manager
from .Models import (
    ExtensionInstallState,
    MarketExtension,
    MarketOperationResult,
    MarketRelease,
)

# 扩展市场注册表地址（GitHub 托管的 JSON 索引）
MARKET_REGISTRY_URL = 'https://raw.githubusercontent.com/MineJPGcraft/UniBot.Market/main/extensions.json'


# ===== 市场扩展包解压 =====


def extract_market_package(archive_data: bytes, target_dir: Path) -> ExtensionManifest:
    """安全解压市场扩展包并读取其清单，返回清单信息。"""
    try:
        safe_extract_zip(archive_data, target_dir)
    except ArchiveError as error:
        raise ManifestError(str(error)) from error
    return _read_manifest_from_dir(target_dir)


def _read_manifest_from_dir(target_dir: Path) -> ExtensionManifest:
    """从解压目录读取并解析 Extension.toml。"""
    manifest_files = [path for path in target_dir.rglob('Extension.toml')]
    if not manifest_files:
        raise ManifestError('Extension package is missing the Extension.toml manifest!')
    manifest_path = manifest_files[0]
    relative = manifest_path.relative_to(target_dir)
    # 清单必须位于包根目录（根级 Extension.toml 或 <id>/Extension.toml），不允许嵌套在更深层级
    if len(relative.parts) > 2:
        raise ManifestError('Extension.toml must be located at the extension package root!')
    try:
        return parse_manifest(manifest_path.read_text('Utf-8'))
    except Exception as error:
        raise ManifestError(f'Failed to parse extension package manifest: {error}') from error


class ExtensionMarketManager:
    """扩展市场管理器单例。"""

    def __init__(self) -> None:
        self.market_cache: dict[str, MarketExtension] = {}
        self.market_cache_time: float = 0
        # 以扩展 id 为粒度的操作锁：安装 / 升级 / 卸载串行化，避免状态快照互相覆盖
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, extension_id: str) -> asyncio.Lock:
        """获取（或懒创建）指定扩展的操作锁。"""
        lock = self._locks.get(extension_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[extension_id] = lock
        return lock

    # ===== 注册表：拉取 / 缓存 / 视图 =====

    async def fetch_market(self, force: bool = False) -> list[dict]:
        """获取扩展市场注册表（带缓存），失败时返回缓存的空列表。"""
        now = time.time()
        if not force and self.market_cache and now - self.market_cache_time < MARKET_CACHE_TTL:
            return self._build_market_entries()
        data = await request(MARKET_REGISTRY_URL)
        if not isinstance(data, list):
            logger.warning('Failed to fetch extension market data, possibly a network issue.')
            return self._build_market_entries()
        self.market_cache = self._index(data)
        self.market_cache_time = now
        logger.success(f'Extension market refreshed: {len(self.market_cache)} extensions indexed.')
        return self._build_market_entries()

    def _index(self, data: list) -> dict[str, MarketExtension]:
        """把注册表原始列表解析为 id -> MarketExtension（跳过非法条目）。"""
        market: dict[str, MarketExtension] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                extension = MarketExtension.model_validate(item)
            except Exception as error:
                logger.warning(f'Market entry validation failed: {error}, skipped.')
                continue
            market[extension.id] = extension
        return market

    def _build_market_entries(self) -> list[dict]:
        """按 WebUI 契约构造市场列表展示字典（含兼容版本标记与默认安装目标）。"""
        entries: list[dict] = []
        for extension in self.market_cache.values():
            compatible = extension.compatible_release()
            latest = extension.latest_release()
            # 代码型扩展在 registry，无代码扩展包（template/resources）在 no_code_info
            installed = extension.id in extension_manager.registry or extension.id in extension_manager.no_code_info
            info = extension_manager.get_extension_info(extension.id) if installed else {}
            target = compatible or latest
            entries.append(
                {
                    'id': extension.id,
                    'name': extension.name,
                    'repo': extension.repo,
                    'description': extension.description,
                    'official': extension.official,
                    # 最新版本（可能不兼容当前核心版本）
                    'latest_version': latest.version if latest else '',
                    'latest_unibot': latest.unibot_version if latest else '*',
                    'latest_compatible': bool(latest) and is_unibot_compatible(latest.unibot_version),
                    # 默认安装目标：兼容当前 UniBot 版本的最新发布
                    'target_version': target.version if target else '',
                    'target_unibot': target.unibot_version if target else '*',
                    'compatible': compatible is not None,
                    'has_compatible_fallback': bool(compatible and latest and compatible.version != latest.version),
                    'installed': installed,
                    'installed_version': info.get('version', ''),
                    'unibot_version': get_unibot_version(),
                }
            )
        return entries

    def get_releases(self, extension_id: str) -> list[dict]:
        """列出某扩展的全部可选版本（标记兼容当前核心版本与是否已安装）。"""
        extension = self.market_cache.get(extension_id)
        if extension is None:
            return []
        state = self.get_install_state(extension_id)
        installed_version = state.version if state is not None else ''
        return [
            {
                'version': release.version,
                'unibot_version': release.unibot_version,
                'compatible': is_unibot_compatible(release.unibot_version),
                'installed': release.version == installed_version,
            }
            for release in reversed(extension.releases)
        ]

    # ===== 安装状态：States.toml 读写 =====

    def _read_states(self) -> dict[str, ExtensionInstallState]:
        """读取全部扩展安装状态，缺失时返回空字典。"""
        path = STATES_PATH
        if not path.exists():
            return {}
        try:
            data = tomlkit.parse(path.read_text('Utf-8'))
        except Exception as error:
            # 损坏时先备份原文件，避免后续写入直接覆盖导致不可恢复
            backup = path.with_name(f'{path.name}.corrupt.{int(time.time())}')
            path.replace(backup)
            logger.error(f'Failed to read extension install states ({error}); backed up to {backup}.')
            return {}
        states: dict[str, ExtensionInstallState] = {}
        for extension_id, raw in data.items():
            if not isinstance(raw, dict):
                continue
            try:
                states[extension_id] = ExtensionInstallState.model_validate(raw)
            except Exception as error:
                logger.warning(f'Install state validation failed for extension {extension_id}: {error}, skipped.')
        return states

    def _write_states(self, states: dict[str, ExtensionInstallState]) -> None:
        """原子写入全部扩展安装状态（临时文件 + 替换，失败保留旧状态）。"""
        data = {extension_id: state.model_dump() for extension_id, state in states.items()}
        atomic_write(STATES_PATH, tomlkit.dumps(data))

    def get_install_state(self, extension_id: str) -> ExtensionInstallState | None:
        """获取指定扩展的安装状态，未安装返回 None。"""
        return self._read_states().get(extension_id)

    # ===== 版本选择（纯逻辑） =====

    @staticmethod
    def _select_release(extension_entry: MarketExtension, version: str) -> tuple[MarketRelease | None, str]:
        """
        选择要安装的发布版本，返回 (发布条目, 失败消息键)。

        显式指定版本时按版本号精确查找（允许安装历史版本以回退）；未指定时自动挑选
        兼容当前 UniBot 版本的最新发布，无任何兼容版本则拒绝安装。
        """
        if version:
            release = extension_entry.find_release(version)
            if release is None:
                return None, 'extensions.market_version_not_found'
            return release, ''
        if (compatible := extension_entry.compatible_release()) is not None:
            return compatible, ''
        return None, 'extensions.unsupported_version'

    # ===== 安装：下载 / 事务 / 记录 =====

    async def install(self, extension_id: str, version: str = '') -> MarketOperationResult:
        """从市场安装/升级扩展（可回滚事务），重启后由 Loader 加载生效。"""
        async with self._lock_for(extension_id):
            return await self._install_locked(extension_id, version)

    async def _install_locked(self, extension_id: str, version: str) -> MarketOperationResult:
        """安装事务主体：以扩展 id 为粒度串行执行（调用方须持有该扩展的锁）。"""
        extension_entry = self.market_cache.get(extension_id)
        if extension_entry is None:
            return MarketOperationResult(False, 'extensions.market_not_found_in_cache', {'id': extension_id})
        release, error_key = self._select_release(extension_entry, version)
        if release is None:
            return MarketOperationResult(False, error_key, {'id': extension_id, 'version': version})
        # 语义化提示：最新版不兼容当前核心版本时，说明回退到了哪个历史版本
        latest = extension_entry.latest_release()
        warning_key = ''
        if not version and latest is not None and release.version != latest.version:
            warning_key = 'extensions.install_compatible_fallback'
        try:
            archive_data = await self._download_release(release.asset_url, release.sha256)
            # 安装事务：解压到临时目录，校验清单后原子替换（重 IO 放入线程，避免阻塞事件循环）
            success, message = await asyncio.to_thread(self._install_transaction, extension_id, archive_data, release)
            if not success:
                return MarketOperationResult(
                    False, 'extensions.install_failed_reason', {'error': message}, error=message
                )
            # 记录安装状态（来源/版本/sha256/依赖归属）
            await asyncio.to_thread(self._record_install, extension_id, release, archive_data, extension_entry)
            # 依赖声明与安装由任务中心在后台执行（uv add + uv sync），此处不阻塞安装请求
            return MarketOperationResult(
                True,
                'extensions.install_success',
                {'id': extension_id, 'version': release.version},
                version=release.version,
                warning_key=warning_key,
                warning_params={
                    'id': extension_id,
                    'version': release.version,
                    'latest': latest.version if latest else '',
                },
            )
        except ManifestError as error:
            return MarketOperationResult(
                False, 'extensions.install_failed_reason', {'error': str(error)}, error=str(error)
            )
        except Exception as error:
            exception_logger.error('Extension installation failed!')
            return MarketOperationResult(
                False, 'extensions.install_failed_reason', {'error': str(error)}, error=str(error)
            )

    async def _download_release(self, asset_url: str, expected_sha256: str) -> bytes:
        """下载扩展包并校验 SHA-256，失败抛 ManifestError。"""
        response = await github_download(asset_url)
        if response is None:
            raise ManifestError(f'Failed to download extension package: {asset_url}')
        archive_data = response.getvalue()
        if expected_sha256:
            actual = hashlib.sha256(archive_data).hexdigest()
            if actual.lower() != expected_sha256.lower():
                raise ManifestError(
                    f'Extension package SHA-256 verification failed (expected {expected_sha256}, got {actual})!'
                )
        return archive_data

    def _install_transaction(self, extension_id: str, archive_data: bytes, release: MarketRelease) -> tuple[bool, str]:
        """在临时目录解压校验，成功后原子替换目标目录（同步阻塞，调用方需放入线程）。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            try:
                manifest = extract_market_package(archive_data, temp_dir_path)
            except ManifestError as error:
                return False, str(error)
            # 校验解压后的清单 id 与目标一致
            if manifest.extension.id != extension_id:
                return False, f'扩展包清单 id {manifest.extension.id} 与目标 {extension_id} 不一致！'
            # 校验兼容性（与 Loader 共用同一实现）
            try:
                validate_unibot_constraint(extension_id, manifest.compatibility.unibot)
            except ExtensionError as error:
                return False, str(error)
            # 原子替换：先备份旧目录，再替换，失败回滚
            target_dir = EXTENSIONS_DIR / extension_id
            backup_dir: Path | None = None
            if target_dir.exists():
                backup_dir = target_dir.with_suffix('.backup')
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                target_dir.rename(backup_dir)
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(temp_dir_path, target_dir, dirs_exist_ok=True)
            except Exception as error:
                # 回滚：恢复备份目录
                if backup_dir and backup_dir.exists():
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    backup_dir.rename(target_dir)
                return False, f'扩展包解压替换失败：{error}'
            # 清理备份（升级成功）
            if backup_dir and backup_dir.exists():
                shutil.rmtree(backup_dir)
        return True, 'ok'

    def _record_install(
        self,
        extension_id: str,
        release: MarketRelease,
        archive_data: bytes,
        extension_entry: MarketExtension,
    ) -> None:
        """记录扩展安装状态与 Python 依赖归属（同步阻塞，调用方需放入线程）。"""
        states = self._read_states()
        manifest = None
        # 尝试从已安装目录读取清单以获取 Python 依赖
        target_dir = EXTENSIONS_DIR / extension_id
        manifest_path = next(target_dir.glob('Extension.toml'), None)
        if manifest_path is not None:
            try:
                manifest = parse_manifest(manifest_path.read_text('Utf-8'))
            except Exception:
                manifest = None
        python_dependencies = list(manifest.dependencies.python) if manifest is not None else []
        states[extension_id] = ExtensionInstallState(
            source='market',
            version=release.version,
            sha256=hashlib.sha256(archive_data).hexdigest(),
            installed_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            repo=extension_entry.repo,
            python_dependencies=python_dependencies,
        )
        self._write_states(states)

    # ===== 卸载 =====

    async def uninstall(self, extension_id: str) -> MarketOperationResult:
        """卸载市场扩展：删除目录并清理安装状态，重启后由 Loader 不再加载。"""
        async with self._lock_for(extension_id):
            return await self._uninstall_locked(extension_id)

    async def _uninstall_locked(self, extension_id: str) -> MarketOperationResult:
        """卸载事务主体：以扩展 id 为粒度串行执行（调用方须持有该扩展的锁）。"""
        target_dir = EXTENSIONS_DIR / extension_id
        if not target_dir.exists() and extension_id not in self.market_cache:
            return MarketOperationResult(False, 'extensions.not_found', {'extension_id': extension_id})
        # 清理安装状态：依赖声明的移除与卸载由任务中心的依赖同步统一处理
        states = await asyncio.to_thread(self._read_states)
        state = states.get(extension_id)
        # 本地扩展（无状态记录但目录存在，或状态来源非 market）不允许市场卸载
        is_local = state is None and target_dir.exists()
        if is_local or (state is not None and state.source != 'market'):
            return MarketOperationResult(False, 'extensions.uninstall_local_refused', {'id': extension_id})
        if target_dir.exists():
            await asyncio.to_thread(shutil.rmtree, target_dir)
        if extension_id in states:
            del states[extension_id]
            await asyncio.to_thread(self._write_states, states)
        logger.success(f'Extension {extension_id} uninstalled, takes effect after restart.')
        return MarketOperationResult(True, 'extensions.uninstall_success', {'id': extension_id})


market_manager = ExtensionMarketManager()
