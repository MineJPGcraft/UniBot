"""
扩展市场管理器：注册表获取、安全安装/卸载事务与安装状态持久化。

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
from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

from Core.Constants import MARKET_CACHE_TTL
from Core.Logging import exception_logger, logger
from Core.Network import github_download, request

from ..Errors import ExtensionError, ManifestError
from ..Manifest import get_unibot_version, is_unibot_compatible, parse_manifest, validate_unibot_constraint
from ..Runtime.Loader import EXTENSIONS_DIR, STATES_FILE, STATES_ROOT
from ..Runtime.Manager import extension_manager
from .Market import (
    ExtensionInstallState,
    MarketExtension,
    MarketRelease,
    extract_market_package,
)

# 扩展市场注册表地址（GitHub 托管的 JSON 索引）
MARKET_REGISTRY_URL = 'https://raw.githubusercontent.com/MineJPGcraft/UniBot.Market/main/extensions.json'


@dataclass(slots=True)
class MarketReleaseOption:
    """单个可选发布版本（供 WebUI 版本切换下拉）。"""

    version: str
    unibot_version: str
    compatible: bool
    installed: bool = False


@dataclass(slots=True)
class InstallResult:
    """安装结果（msg_key / msg_params 供 WebUI 按界面语言翻译）。"""

    success: bool
    msg_key: str
    msg_params: dict = field(default_factory=dict)
    version: str = ''
    warning_key: str = ''
    warning_params: dict = field(default_factory=dict)
    error: str = ''


class ExtensionMarketManager:
    """扩展市场管理器单例。"""

    def __init__(self) -> None:
        self.market_cache: dict[str, MarketExtension] = {}
        self.market_cache_time: float = 0

    # ===== 注册表 =====

    async def fetch_market(self, force: bool = False) -> list[dict]:
        """获取扩展市场注册表（带缓存），失败时返回缓存的空列表。"""
        now = time.time()
        if not force and self.market_cache and now - self.market_cache_time < MARKET_CACHE_TTL:
            return self._market_dicts()
        data = await request(MARKET_REGISTRY_URL)
        if not isinstance(data, list):
            logger.warning('Failed to fetch extension market data, possibly a network issue.')
            return self._market_dicts()
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
        self.market_cache = market
        self.market_cache_time = now
        logger.success(f'Extension market refreshed: {len(market)} extensions indexed.')
        return self._market_dicts()

    def _market_dicts(self) -> list[dict]:
        """将市场缓存转换为 WebUI 展示用的字典列表（含兼容版本标记）。"""
        items = []
        for extension in self.market_cache.values():
            compatible = extension.compatible_release()
            latest = extension.latest_release()
            # 代码型扩展在 registry，无代码扩展包（template/resources）在 no_code_info
            installed = extension.id in extension_manager.registry or extension.id in extension_manager.no_code_info
            info = extension_manager.get_extension_info(extension.id) if installed else {}
            target = compatible or latest
            items.append(
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
        return items

    def get_releases(self, extension_id: str) -> list[MarketReleaseOption]:
        """列出某扩展的全部可选版本（标记兼容当前核心版本与是否已安装）。"""
        extension = self.market_cache.get(extension_id)
        if extension is None:
            return []
        state = self.get_install_state(extension_id)
        installed_version = state.version if state is not None else ''
        return [
            MarketReleaseOption(
                version=release.version,
                unibot_version=release.unibot_version,
                compatible=is_unibot_compatible(release.unibot_version),
                installed=release.version == installed_version,
            )
            for release in reversed(extension.releases)
        ]

    # ===== 安装状态持久化 =====

    def _states_path(self) -> Path:
        """返回 States.toml 的完整路径。"""
        return STATES_ROOT / STATES_FILE

    def _read_states(self) -> dict[str, ExtensionInstallState]:
        """读取全部扩展安装状态，缺失时返回空字典。"""
        path = self._states_path()
        if not path.exists():
            return {}
        try:
            data = tomlkit.parse(path.read_text('Utf-8'))
        except Exception as error:
            logger.warning(f'Failed to read extension install states: {error}, treated as empty.')
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
        """原子写入全部扩展安装状态。"""
        data = {extension_id: state.model_dump() for extension_id, state in states.items()}
        path = self._states_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tomlkit.dumps(data), encoding='Utf-8')

    def get_install_state(self, extension_id: str) -> ExtensionInstallState | None:
        """获取指定扩展的安装状态，未安装返回 None。"""
        return self._read_states().get(extension_id)

    # ===== 下载与校验 =====

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

    # ===== 安装事务 =====

    async def install(self, extension_id: str, version: str = '') -> InstallResult:
        """从市场安装/升级扩展（可回滚事务），重启后由 Loader 加载生效。"""
        extension_entry = self.market_cache.get(extension_id)
        if extension_entry is None:
            return InstallResult(False, 'extensions.market_not_found_in_cache', {'id': extension_id})
        release, error_key = self._select_release(extension_entry, version)
        if release is None:
            return InstallResult(False, error_key, {'id': extension_id, 'version': version})
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
                return InstallResult(False, 'extensions.install_failed_reason', {'error': message}, error=message)
            # 记录安装状态（来源/版本/sha256/依赖归属）
            await asyncio.to_thread(self._record_install, extension_id, release, archive_data, extension_entry)
            # 依赖声明与安装由任务中心在后台执行（uv add + uv sync），此处不阻塞安装请求
            return InstallResult(
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
            return InstallResult(False, 'extensions.install_failed_reason', {'error': str(error)}, error=str(error))
        except Exception as error:
            exception_logger.error('Extension installation failed!')
            return InstallResult(False, 'extensions.install_failed_reason', {'error': str(error)}, error=str(error))

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
                return False, (f'扩展包清单 id {manifest.extension.id} 与目标 {extension_id} 不一致！')
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

    async def uninstall(self, extension_id: str) -> tuple[bool, str]:
        """卸载市场扩展：删除目录并清理安装状态，重启后由 Loader 不再加载。"""
        target_dir = EXTENSIONS_DIR / extension_id
        if not target_dir.exists() and extension_id not in self.market_cache:
            return False, f'扩展 {extension_id} 不存在'
        # 清理安装状态：依赖声明的移除与卸载由任务中心的依赖同步统一处理
        states = await asyncio.to_thread(self._read_states)
        state = states.get(extension_id)
        # 本地扩展（无安装状态记录或非市场来源）不允许卸载
        if state is None:
            if target_dir.exists():
                return False, f'扩展 {extension_id} 是本地扩展，不允许卸载'
        elif state.source != 'market':
            return False, f'扩展 {extension_id} 是本地扩展，不允许卸载'
        if target_dir.exists():
            await asyncio.to_thread(shutil.rmtree, target_dir)
        if extension_id in states:
            del states[extension_id]
            await asyncio.to_thread(self._write_states, states)
        logger.success(f'Extension {extension_id} uninstalled, takes effect after restart.')
        return True, f'Extension {extension_id} uninstalled, takes effect after restart.'


market_manager = ExtensionMarketManager()
