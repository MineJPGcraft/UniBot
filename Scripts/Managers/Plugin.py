import time

import nonebot

from Scripts.Constants import BUILTIN_PLUGIN_PREFIX, MARKET_CACHE_TTL
from Scripts.Logging import logger
from Scripts.Managers import config_manager
from Scripts.Network import request


class PluginManager:
    """插件管理器，管理 pyproject.toml 中登记的插件、依赖插件与插件市场。"""

    # 插件市场注册表地址（NoneBot 官方插件市场）
    MARKET_URL = 'https://registry.nonebot.dev/plugins.json'

    def __init__(self) -> None:
        self.market_cache: list = []
        self.market_cache_time: float = 0

    def _configured_plugins(self) -> list[dict]:
        """获取 pyproject.toml 中登记的插件配置。"""
        configured_plugins = []
        for plugin in config_manager.nonebot_config.get('plugins', []):
            if isinstance(plugin, str):
                configured_plugins.append({'module_name': plugin, 'enabled': True})
            elif plugin.get('module_name'):
                configured_plugins.append(plugin)
        return configured_plugins

    @staticmethod
    def _can_disable(module_name: str) -> bool:
        """框架内置插件（`BUILTIN_PLUGIN_PREFIX` 前缀）不允许禁用。"""
        return not module_name.startswith(BUILTIN_PLUGIN_PREFIX)

    @staticmethod
    def _plugin_info(plugin, configured: dict | None = None) -> dict:
        if not plugin and configured is None:
            raise ValueError('plugin and configured cannot both be empty')
        metadata = plugin.metadata if plugin else None
        module_name = plugin.module_name if plugin else configured['module_name']
        extra = metadata.extra if metadata else {}
        return {
            'name': plugin.name if plugin else module_name.rsplit('.', 1)[-1],
            'module_name': module_name,
            'display_name': metadata.name if metadata else module_name.rsplit('.', 1)[-1],
            'version': extra.get('version', '') if metadata else '',
            'description': metadata.description if metadata else '',
            'author': extra.get('author', '') if metadata else '',
            'homepage': metadata.homepage if metadata else '',
            'enabled': configured.get('enabled', True) if configured else True,
            'type': 'builtin' if module_name.startswith(BUILTIN_PLUGIN_PREFIX) else 'external',
            'can_disable': PluginManager._can_disable(module_name),
            'dependencies': [],
            'config_schema': {},
        }

    def get_installed_plugins(self) -> list[dict]:
        """获取登记插件和未登记依赖插件的详细信息。"""
        loaded_plugins = {plugin.module_name: plugin for plugin in nonebot.get_loaded_plugins()}
        plugins = []
        configured_modules = set()
        for configured in self._configured_plugins():
            module_name = configured['module_name']
            configured_modules.add(module_name)
            plugins.append(self._plugin_info(loaded_plugins.get(module_name), configured))
        for module_name, plugin in loaded_plugins.items():
            if module_name not in configured_modules:
                info = self._plugin_info(plugin)
                info['type'] = 'dependency'
                info['can_disable'] = False
                plugins.append(info)
        return plugins

    def get_plugin_detail(self, name: str) -> dict | None:
        """获取指定插件详情。"""
        for plugin in self.get_installed_plugins():
            if plugin['name'] == name or plugin['module_name'] == name:
                return plugin
        return None

    async def set_enabled(self, name: str, enabled: bool) -> bool:
        """设置可管理插件的启停状态，重启后生效。"""
        plugin = self.get_plugin_detail(name)
        if not plugin or not plugin['can_disable']:
            return False
        config_manager.set_plugin_enabled(plugin['module_name'], enabled)
        return True

    # ===== 插件市场 =====

    async def fetch_market(self, force: bool = False) -> list[dict]:
        """获取插件市场数据（带缓存），请求失败时返回空列表。"""
        now = time.time()
        if not force and self.market_cache and now - self.market_cache_time < MARKET_CACHE_TTL:
            return self.market_cache
        data = await request(self.MARKET_URL)
        if not isinstance(data, list):
            logger.warning('Failed to fetch plugin market data, possibly a network issue.')
            return self.market_cache
        self.market_cache = [item for item in data if isinstance(item, dict)]
        self.market_cache_time = now
        logger.success(f'Plugin market refreshed: <yellow>{len(self.market_cache)}</yellow> plugins indexed.')
        return self.market_cache

    async def install(self, project_link: str, module_name: str, version: str = '') -> tuple[bool, str]:
        """从市场安装插件：登记依赖并注册插件，重启后由 Watchdog 自动 uv sync 安装。"""
        package = f'{project_link}=={version}' if version else project_link
        config_manager.add_dependency(package)
        config_manager.add_plugin(module_name)
        logger.success(f'Plugin <green>{project_link}</green> registered for install.')
        return True, '安装成功，重启后生效'

    async def upgrade(self, project_link: str, module_name: str, version: str = '') -> tuple[bool, str]:
        """升级市场插件：更新依赖登记并确保注册，重启后由 Watchdog 自动 uv sync 更新。"""
        package = f'{project_link}=={version}' if version else project_link
        config_manager.remove_dependency(project_link)
        config_manager.add_dependency(package)
        config_manager.set_plugin_enabled(module_name, True)
        logger.success(f'Plugin <green>{project_link}</green> registered for upgrade.')
        return True, '升级成功，重启后生效'

    async def uninstall(self, project_link: str, module_name: str) -> tuple[bool, str]:
        """卸载市场插件：移除登记，重启后由 Watchdog 自动 uv sync 卸载。"""
        config_manager.remove_plugin(module_name)
        config_manager.remove_dependency(project_link)
        logger.success(f'Plugin <green>{project_link}</green> registered for uninstall.')
        return True, '卸载成功，重启后生效'


plugin_manager = PluginManager()
