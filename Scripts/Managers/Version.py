import asyncio
import shutil
import tempfile
from pathlib import Path

import tomlkit

from Scripts.Logging import logger
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

    def check_update(self) -> bool:
        """当前版本是否落后于最新版本。"""
        return self.latest_version is not None and self.latest_version != self.version

    async def init(self):
        """记录当前版本，并在后台异步拉取最新版本。"""
        self.version = str(config_manager.version)
        logger.info(f'监测到当前为 {self.version} 版本。')
        await self.fetch_latest()

    async def fetch_latest(self) -> bool:
        """从 GitHub 拉取最新发布版本，成功返回 True。"""
        latest_data = await request(LATEST_RELEASE_API)
        if not latest_data:
            logger.warning('获取最新版本失败，请检查网络稍后再试！')
            return False
        self.latest_version = str(latest_data.get('tag_name', ''))
        if not self.latest_version:
            logger.warning('获取最新版本失败：返回数据缺少版本信息！')
            return False
        self.latest_asset_url = self.find_bot_asset(latest_data)
        if self.check_update():
            logger.info(f'发现新版本 {self.latest_version}，当前版本为 {self.version}！')
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
            logger.warning(f'更新失败：{error_message}')
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
                    return '压缩包内缺少核心目录，已取消更新！'
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
                        logger.debug(f'已覆盖根目录文件 {file_name}。')
                # pyproject.toml 仅同步版本号，保留本地其余配置
                self._sync_version_from_archive(temp_dir / 'pyproject.toml')
            logger.success('已将核心代码更新为最新版本！')
            return None
        except Exception as error:
            logger.warning(f'更新解压失败：{error}')
            return '更新失败，请查看控制台日志！'

    def _sync_version_from_archive(self, archive_pyproject: Path) -> None:
        """从压缩包 pyproject.toml 同步项目版本与 WebUI 版本到本地，保留本地其余配置。"""
        if not archive_pyproject.is_file():
            logger.warning('压缩包内缺少 pyproject.toml，跳过版本同步！')
            return
        try:
            archive_data = tomlkit.parse(archive_pyproject.read_text('Utf-8'))
            new_version = archive_data.get('project', {}).get('version', '')
            new_webui_version = archive_data.get('tool', {}).get('unibot', {}).get('webui_version', '')
            if not new_version:
                logger.warning('压缩包 pyproject.toml 缺少版本号，跳过版本同步！')
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
            logger.info(f'已将项目版本同步为 {new_version}，WebUI 版本同步为 {new_webui_version}！')
        except Exception as error:
            logger.warning(f'同步版本号失败：{error}')


version_manager = VersionManager()
