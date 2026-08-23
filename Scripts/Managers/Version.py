import asyncio
import shutil
import tempfile
from pathlib import Path

import tomlkit

from Scripts.Config import config
from Scripts.Logging import exception_logger, logger
from Scripts.Network import github_download, request

from .Config import config_manager

# Release 资产中 UniBot.zip 的资源名
UNIBOT_ZIP_ASSET = 'UniBot.zip'
LATEST_RELEASE_API = 'https://api.github.com/repos/MineJPGcraft/UniBot/releases/latest'


class VersionManager:
    """版本管理器，负责读取当前版本、检测并更新到 GitHub 上的最新发布版本。"""

    version: str = ''
    latest_version: str | None = None
    latest_asset_url: str | None = None

    def __init__(self):
        self.notified_version: str | None = None
        self._notify_lock = asyncio.Lock()

    def check_update(self) -> bool:
        """当前版本是否落后于最新版本。"""
        return self.latest_version is not None and self.latest_version != self.version

    async def try_notify_update(self) -> None:
        """机器人连接或版本检测完成后，向消息群推送一次更新提醒（每个版本仅推送一次）。"""
        if not config.broadcast_update or not self.check_update():
            return
        async with self._notify_lock:
            if self.notified_version == self.latest_version:
                return
            
            # 函数内导入：本模块位于插件加载前的早期导入链，禁止顶层引入插件托管包（alconna / uninfo）
            from Scripts.Utils import send_message_to_groups

            if await send_message_to_groups(f'检测到新版本 {self.latest_version}，请及时更新！'):
                self.notified_version = self.latest_version
                logger.info('Update notice sent to message groups.')

    async def init(self):
        """记录当前版本，并在后台异步拉取最新版本。"""
        self.version = str(config_manager.version)
        logger.info(f'Current version: {self.version}.')
        await self.fetch_latest()
        if self.check_update():
            self.print_update_notice()
        # 版本检测可能晚于机器人连接完成，此处兜底补发一次（内部有去重保护）
        await self.try_notify_update()

    def print_update_notice(self) -> None:
        """检测到新版本时在控制台输出黄色加粗下划线的更新提醒。"""
        logger.info(
            f'<yellow><bold><underline>检测到新版本请及时更新</underline></bold></yellow>'
            f'（当前 {self.version}，最新 {self.latest_version}）'
        )

    async def fetch_latest(self) -> bool:
        """从 GitHub 拉取最新发布版本，成功返回 True。"""
        latest_data = await request(LATEST_RELEASE_API)
        if not latest_data:
            logger.warning('Failed to fetch the latest version, check your network and retry later.')
            return False
        self.latest_version = str(latest_data.get('tag_name', ''))
        if not self.latest_version:
            logger.warning('Failed to fetch the latest version: response is missing version info.')
            return False
        self.latest_asset_url = self.find_bot_asset(latest_data)
        if self.check_update():
            logger.info(f'New version {self.latest_version} available, current version is {self.version}.')
        return True

    @staticmethod
    def find_bot_asset(release_data: dict) -> str | None:
        """从 Release 数据中查找 UniBot.zip 资产的下载地址。"""
        for asset in release_data.get('assets', []) or []:
            if asset.get('name') == UNIBOT_ZIP_ASSET:
                return asset.get('browser_download_url')
        return None

    async def update(self) -> str | None:
        """从 GitHub Release 下载最新代码并替换核心代码，成功返回 None，失败返回错误信息。"""
        if not await self.fetch_latest():
            return '更新失败，请检查网络稍后再试！'
        asset_url = self.latest_asset_url
        if not asset_url:
            return '更新失败，最新版本缺少 UniBot.zip 资源！'
        archive = await github_download(asset_url)
        if archive is None:
            return '更新失败，下载 UniBot.zip 失败，请检查网络稍后再试！'
        error_message = await asyncio.to_thread(self._apply_update, archive.getvalue())
        if error_message:
            logger.warning(f'Update failed: {error_message}')
            return error_message
        return None

    def _apply_update(self, archive_data: bytes) -> str | None:
        """安全解压 UniBot.zip 并替换核心代码，成功返回 None，失败返回错误信息。

        替换范围：Scripts 目录 + 根目录入口文件（Bot.py / Watchdog.py）。
        仅同步 pyproject.toml 的版本号，用户配置（Config.toml / .env 等）一律保留。
        """
        from Scripts.Utils import safe_extract_zip

        scripts_dir = Path('Scripts')
        try:
            with tempfile.TemporaryDirectory() as temp_dir_name:
                temp_dir = Path(temp_dir_name)
                safe_extract_zip(archive_data, temp_dir)
                source = temp_dir / 'Scripts'
                if not source.is_dir():
                    return 'Archive is missing the core directory, update cancelled.'
                backup_dir = scripts_dir.with_name('Scripts.bak')
                shutil.rmtree(backup_dir, ignore_errors=True)
                if scripts_dir.exists():
                    scripts_dir.rename(backup_dir)
                try:
                    source.replace(scripts_dir)
                except Exception:
                    if backup_dir.exists() and not scripts_dir.exists():
                        backup_dir.rename(scripts_dir)
                    raise
                shutil.rmtree(backup_dir, ignore_errors=True)
                # 覆盖根目录入口文件（Bot.py / Watchdog.py），用户配置一律保留
                for file_name in ('Bot.py', 'Watchdog.py'):
                    source_file = temp_dir / file_name
                    if source_file.is_file():
                        shutil.copy2(source_file, Path(file_name))
                        logger.debug(f'Root file {file_name} overwritten.')
                # pyproject.toml 仅同步版本号，保留本地其余配置
                self._sync_version_from_archive(temp_dir / 'pyproject.toml')
            logger.success('Core code updated to the latest version.')
            return None
        except Exception as error:
            exception_logger.warning(f'Failed to extract the update archive: {error}')
            return 'Update failed, please check the console logs.'

    def _sync_version_from_archive(self, archive_pyproject: Path) -> None:
        """从压缩包 pyproject.toml 同步项目版本与 WebUI 版本到本地，保留本地其余配置。"""
        if not archive_pyproject.is_file():
            logger.warning('pyproject.toml missing in the archive, skipping version sync.')
            return
        try:
            archive_data = tomlkit.parse(archive_pyproject.read_text('Utf-8'))
            new_version = archive_data.get('project', {}).get('version', '')
            new_webui_version = archive_data.get('tool', {}).get('unibot', {}).get('webui_version', '')
            if not new_version:
                logger.warning('Archive pyproject.toml has no version field, skipping version sync.')
                return
            local_path = Path('pyproject.toml')
            local_data = tomlkit.parse(local_path.read_text('Utf-8'))
            local_data['project']['version'] = new_version
            if new_webui_version:
                unibot_data = local_data.setdefault('tool', {}).setdefault('unibot', {})
                unibot_data['webui_version'] = new_webui_version
            local_path.write_text(tomlkit.dumps(local_data), encoding='Utf-8')
            self.version = str(new_version)
            config_manager.webui_version = str(new_webui_version)
            logger.info(f'Project version synced to {new_version}, WebUI version synced to {new_webui_version}.')
        except Exception as error:
            logger.warning(f'Failed to sync version numbers: {error}')


version_manager = VersionManager()
