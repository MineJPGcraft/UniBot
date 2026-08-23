import sys
from contextlib import suppress
from json import JSONDecodeError, dumps, loads

import tomlkit

from Scripts.Constants import CONFIG_TOML_PATH, ENV_PATH, MESSAGES_PATH, PYPROJECT_PATH
from Scripts.Logging import logger


class ConfigManager:
    # pyproject.toml 数据
    version: str = ''
    webui_version: str = ''
    nonebot_config: dict = {}
    pyproject_data: dict = {}

    def __init__(self) -> None:
        self.env_path = ENV_PATH
        self.pyproject_path = PYPROJECT_PATH
        self.messages_path = MESSAGES_PATH
        self.config_path = CONFIG_TOML_PATH
        self.mapping: list = []
        self.environment: dict = {}

    @staticmethod
    def _parse_value(raw: str) -> object:
        """解析 .env 值：JSON 优先，其次引号包裹的多行文本。"""
        with suppress(JSONDecodeError):
            return loads(raw)
        for quote in ('"', "'"):
            if not (raw.startswith(quote) and raw.endswith(quote) and len(raw) >= 2):
                continue
                # 引号包裹的 JSON（如 "{"A":"B"}" → 去外层引号解析为 dict）
            with suppress(JSONDecodeError):
                return loads(raw[1:-1])
            # 引号多行文本：去掉首尾引号，把内部真实换行转义成 \n 后重新包上引号，
            # 交给 JSON 解析（自动还原转义），避免保留外层引号
            with suppress(JSONDecodeError):
                return loads(raw.replace('\n', '\\n'))
        return raw

    def init(self):
        """加载 .env 和 pyproject.toml 配置。"""
        self.load_env()
        self.load_pyproject()

    def load_env(self):
        """加载 .env 配置文件（可重复调用，会重置内存缓存）。"""
        if not self.env_path.exists():
            logger.error('Config file not found! Please re-download and try again.')
            sys.exit(1)
        self.mapping = []
        self.environment = {}
        last_key: str | None = None
        for line in self.env_path.read_text('Utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                self.mapping.append(line)
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                last_key = key.strip()
                self.environment[last_key] = value.strip()
                self.mapping.append(last_key)
                continue
            elif last_key is not None:
                # 变量值跨行：续行追加到上一个值（保留换行符）
                self.environment[last_key] += '\n' + line
                continue
            logger.warning(f'Ignoring unparsable line in .env: {line!r}')
        # 先合并原始值，再统一解析，保证引号多行值完整
        self.environment = {key: self._parse_value(raw) for key, raw in self.environment.items()}
        logger.success('.env configuration loaded.')

    def load_pyproject(self):
        """加载 pyproject.toml 配置（版本号、NoneBot 适配器/插件等）。"""
        if not self.pyproject_path.exists():
            logger.error('pyproject.toml not found! Please re-download and try again.')
            sys.exit(1)
        self.pyproject_data = tomlkit.parse(self.pyproject_path.read_text('Utf-8'))
        self.update_pyproject_cache()
        logger.success('pyproject.toml loaded.')

    def update_pyproject_cache(self):
        """更新 pyproject.toml 派生配置缓存。"""
        self.version = self.pyproject_data.get('project', {}).get('version', '')
        tools = self.pyproject_data.get('tool', {})
        self.webui_version = tools.get('unibot', {}).get('webui_version', '')
        self.nonebot_config = tools.get('nonebot', {})

    # ===== .env 操作 =====

    def read_env(self) -> dict:
        """获取 .env 配置字典。"""
        return self.environment

    def update_env(self, new: dict):
        """更新 .env 配置并写回文件。"""
        logger.info(f'Updating configuration: {new}')
        for key, value in new.items():
            self.environment[key] = value
            if key not in self.mapping:
                self.mapping.append(key)
        self.write_env()

    def write_env(self):
        """将 .env 配置写回文件。"""
        lines = []
        for line in self.mapping:
            if line.startswith('#') or not line:
                lines.append(line)
                continue
            lines.append(f'{line}={dumps(self.environment[line], ensure_ascii=False)}')
        self.env_path.write_text('\n'.join(lines), encoding='Utf-8')
        logger.success('Configuration saved. Restart the bot manually for changes to take effect.')

    def write_env_raw(self, content: str):
        """以原始文本内容写回 .env 文件，并同步内存缓存。"""
        self.env_path.write_text(content, encoding='Utf-8')
        self.load_env()
        logger.success('Configuration saved. Restart the bot manually for changes to take effect.')

    # ===== pyproject.toml 操作 =====

    def read_pyproject(self) -> dict:
        """读取内存中的 pyproject.toml 完整内容。"""
        return self.pyproject_data

    def write_pyproject(self, data: dict):
        """更新缓存并写回 pyproject.toml（保留注释和格式）。"""
        self.pyproject_path.write_text(tomlkit.dumps(data), encoding='Utf-8')
        self.pyproject_data = data
        self.update_pyproject_cache()

    def add_adapter(self, name: str, module_name: str) -> bool:
        """添加适配器，返回是否成功（False 表示已存在）。"""
        data = self.read_pyproject()
        adapters = data.setdefault('tool', {}).setdefault('nonebot', {}).setdefault('adapters', [])
        if any(adapter['module_name'] == module_name for adapter in adapters):
            return False
        adapters.append({'name': name, 'module_name': module_name})
        self.write_pyproject(data)
        return True

    def remove_adapter(self, module_name: str):
        """移除适配器（从 pyproject.toml 中删除）。"""
        data = self.read_pyproject()
        adapters = data.get('tool', {}).get('nonebot', {}).get('adapters', [])
        data['tool']['nonebot']['adapters'] = [adapter for adapter in adapters if adapter['module_name'] != module_name]
        self.write_pyproject(data)

    @staticmethod
    def _package_base(dependency: str) -> str:
        """从依赖字符串中提取包名（去除 extras 与版本约束）。"""
        for separator in ('[', '>', '<', '~', '!', '='):
            if separator in dependency:
                dependency = dependency.split(separator, 1)[0]
        return dependency.strip()

    def get_dependencies(self) -> list[str]:
        """获取 pyproject.toml 中登记的依赖列表。"""
        dependencies = self.read_pyproject().get('project', {}).get('dependencies', [])
        return list(dependencies)

    def get_dependency_packages(self) -> set[str]:
        """获取已登记依赖的包名集合（去除 extras 与版本约束）。"""
        return {self._package_base(dependency) for dependency in self.get_dependencies()}

    def remove_dependency(self, package: str):
        """从 pyproject.toml 的 dependencies 中移除指定包。"""
        data = self.read_pyproject()
        dependencies = data.get('project', {}).get('dependencies', [])
        data['project']['dependencies'] = [
            dependency for dependency in dependencies if self._package_base(dependency) != package
        ]
        self.write_pyproject(data)

    def add_dependency(self, package: str):
        """向 pyproject.toml 的 dependencies 中添加包（不重复）。"""
        data = self.read_pyproject()
        dependencies = data.setdefault('project', {}).setdefault('dependencies', [])
        package_bases = {self._package_base(dependency) for dependency in dependencies}
        if self._package_base(package) not in package_bases:
            dependencies.append(package)
            self.write_pyproject(data)

    def add_plugin(self, module_name: str) -> bool:
        """添加插件，返回是否成功（False 表示已存在）。"""
        data = self.read_pyproject()
        plugins = data.setdefault('tool', {}).setdefault('nonebot', {}).setdefault('plugins', [])
        if any(
            plugin == module_name or isinstance(plugin, dict) and plugin.get('module_name') == module_name
            for plugin in plugins
        ):
            return False
        plugins.append({'module_name': module_name, 'enabled': True})
        self.write_pyproject(data)
        return True

    def remove_plugin(self, module_name: str):
        """移除插件。"""
        data = self.read_pyproject()
        plugins = data.get('tool', {}).get('nonebot', {}).get('plugins', [])
        data['tool']['nonebot']['plugins'] = [
            plugin
            for plugin in plugins
            if not (plugin == module_name or isinstance(plugin, dict) and plugin.get('module_name') == module_name)
        ]
        self.write_pyproject(data)

    def set_plugin_enabled(self, module_name: str, enabled: bool):
        """更新 pyproject.toml 中插件的启用状态。"""
        data = self.read_pyproject()
        plugins = data.get('tool', {}).get('nonebot', {}).get('plugins', [])
        plugin_found = False
        for index, plugin in enumerate(plugins):
            if plugin == module_name:
                plugins[index] = {'module_name': module_name, 'enabled': enabled}
                plugin_found = True
                break
            if isinstance(plugin, dict) and plugin.get('module_name') == module_name:
                plugin['enabled'] = enabled
                plugin_found = True
                break
        if not plugin_found:
            plugins.append({'module_name': module_name, 'enabled': enabled})
        data['tool']['nonebot']['plugins'] = plugins
        self.write_pyproject(data)

    # ===== Config.toml 操作 =====

    def read_config_raw(self) -> str:
        """读取 Config.toml 原始文本内容。"""
        return self.config_path.read_text('Utf-8')

    def update_config(self, data: dict) -> None:
        """更新 Config.toml 指定键并写回（保留注释与格式）。"""
        try:
            toml_document = tomlkit.parse(self.config_path.read_text('Utf-8'))
        except FileNotFoundError:
            toml_document = tomlkit.document()
        for key, value in data.items():
            if isinstance(value, dict) and key in toml_document and isinstance(toml_document[key], dict):
                for sub_key, sub_value in value.items():
                    toml_document[key][sub_key] = sub_value
                continue
            toml_document[key] = value
        self.config_path.write_text(tomlkit.dumps(toml_document), encoding='Utf-8')

    # ===== Messages.toml 操作 =====

    def read_messages_raw(self) -> str:
        """读取 Messages.toml 原始文本内容。"""
        return self.messages_path.read_text('Utf-8')

    def write_messages_raw(self, content: str):
        """以原始文本写回 Messages.toml，并校验语法。"""
        tomlkit.parse(content)
        self.messages_path.write_text(content, encoding='Utf-8')
        # 函数内导入：Scripts.Messages 被 Scripts.Config 等模块加载链引用，延迟到调用时避免环
        from Scripts.Messages import reload_messages

        reload_messages()
        logger.success('Message texts saved and reloaded.')


config_manager = ConfigManager()
