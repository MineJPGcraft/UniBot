"""
NoneBot 插件登记与启停的运行时存储（Config/Plugins.toml）。

插件登记属于运行时状态，不再写入 `pyproject.toml` 的 `[tool.nonebot].plugins`；
框架内置插件随源码分发、由 Bootstrap 程序化加载，不在此文件中登记。
"""

from __future__ import annotations

from pathlib import Path

import tomlkit

from Core.Constants import BUILTIN_PLUGIN_PREFIX, CONFIG_PLUGINS_FILE
from Core.Logging import logger


class PluginRegistry:
    """Config/Plugins.toml 读写：插件模块登记、启停与依赖包记录。"""

    def __init__(self, path: Path = CONFIG_PLUGINS_FILE) -> None:
        self.path = path

    def _load(self) -> dict:
        """读取登记文件，缺失或损坏时返回空 dict。"""
        if not self.path.exists():
            return {}
        try:
            return dict(tomlkit.parse(self.path.read_text('Utf-8')).get('Plugins', {}))
        except Exception as error:
            logger.warning(f'Failed to read plugin registry: {error}, treated as empty.')
            return {}

    def _save(self, plugins: dict) -> None:
        """把登记表写回文件（保留可读格式）。"""
        document = tomlkit.document()
        section = tomlkit.table(is_super_table=True)
        for module_name, config in plugins.items():
            entry = tomlkit.table()
            for key, value in config.items():
                entry[key] = value
            section[module_name] = entry
        document['Plugins'] = section
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(tomlkit.dumps(document), encoding='Utf-8')

    def list_plugins(self) -> list[dict]:
        """列出全部已登记插件（含框架内置项的规整结果）。"""
        plugins = []
        for module_name, config in self._load().items():
            entry = {'module_name': module_name}
            entry.update(config)
            plugins.append(entry)
        return plugins

    def get(self, module_name: str) -> dict | None:
        """获取单个插件的登记配置。"""
        for plugin in self.list_plugins():
            if plugin['module_name'] == module_name:
                return plugin
        return None

    @staticmethod
    def is_builtin(module_name: str) -> bool:
        """是否为框架内置插件（随源码分发、不允许经 WebUI 停用）。"""
        return module_name.startswith(BUILTIN_PLUGIN_PREFIX)

    def add(self, module_name: str, *, dependency_packages: list[str] | None = None) -> bool:
        """登记插件并默认启用，返回是否新增（False 表示已登记）。"""
        plugins = self._load()
        if module_name in plugins:
            return False
        entry = {'module_name': module_name, 'enabled': True}
        if dependency_packages:
            entry['dependency_packages'] = list(dependency_packages)
        plugins[module_name] = entry
        self._save(plugins)
        logger.info(f'Plugin {module_name} registered in Config/Plugins.toml.')
        return True

    def remove(self, module_name: str) -> None:
        """移除插件登记（不触碰依赖声明，依赖移除由 uv 完成任务处理）。"""
        plugins = self._load()
        plugins.pop(module_name, None)
        self._save(plugins)
        logger.info(f'Plugin {module_name} removed from Config/Plugins.toml.')

    def set_enabled(self, module_name: str, enabled: bool) -> None:
        """更新插件启停状态，缺失时补登记。"""
        plugins = self._load()
        entry = dict(plugins.get(module_name, {}))
        entry['module_name'] = module_name
        entry['enabled'] = enabled
        plugins[module_name] = entry
        self._save(plugins)
        logger.info(f'Plugin {module_name} set to {"enabled" if enabled else "disabled"}, takes effect after restart.')

    def enabled_modules(self) -> list[str]:
        """全部已启用插件的模块名（供 Bootstrap 程序化加载）。"""
        return [plugin['module_name'] for plugin in self.list_plugins() if plugin.get('enabled', True)]


plugin_registry = PluginRegistry()
