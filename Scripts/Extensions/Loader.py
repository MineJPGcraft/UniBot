"""扩展发现、依赖拓扑排序与导入加载。"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import tomlkit
from packaging.specifiers import SpecifierSet

from Scripts.Logging import logger

if TYPE_CHECKING:
    from .Manager import ExtensionManager

from Scripts.Config import config

from .Base import (
    Extension,
    ExtensionManifest,
    ExtensionMetadata,
    ExtensionState,
    ExtensionType,
    get_unibot_version,
    manifest_from_attributes,
    parse_manifest,
)
from .Command import (
    BUILTIN_PREFIX,
    command_manager,
)
from .Dependencies import sync_extension_dependencies
from .Errors import (
    CompatibilityError,
    DependencyError,
    LoadError,
    ManifestError,
)
from .Renderer import (
    RendererRegistry,
    TemplateRegistration,
    build_template_config_model,
)
from .Service import ServiceRegistry
from .Storage import (
    ExtensionConfigStore,
    ExtensionDataStore,
)

# 扩展目录根
EXTENSIONS_DIR = Path('Extensions')
# 内置命令扩展目录（框架包内随代码分发）
BUILTIN_DIR = Path(__file__).parent / 'Builtin'
CONFIG_ROOT = Path('Config') / 'Extensions'
CONFIG_EXTENSIONS_FILE = Path('Config') / 'Extensions.toml'
DATA_ROOT = Path('Data') / 'Exs'
STATES_ROOT = Path('Data') / 'Extension'
STATES_FILE = 'States.toml'

# 框架约定文件名
MANIFEST_FILE = 'Extension.toml'


@dataclass
class DiscoveredExtension:
    """发现阶段收集的扩展元信息，供校验、拓扑排序与加载统一访问。"""

    manifest: ExtensionManifest
    directory: Path
    single_file: bool
    enabled: bool
    # 仅单文件扩展存在
    builtin: bool = False
    module_path: str = ''
    # 校验阶段失败原因（版本不兼容/入口缺失），非空表示阻止加载
    blocked_reason: str = ''


class ExtensionLoader:
    """扫描、校验、排序并加载扩展。"""

    def __init__(self, manager: ExtensionManager) -> None:
        self.manager = manager
        # 发现的扩展元信息：id -> DiscoveredExtension
        self._discovered: dict[str, DiscoveredExtension] = {}
        # 已加载的扩展实例（按拓扑顺序）
        self.extensions: list[Extension] = []
        # 已登记的内置命令类，用于判定扩展是否覆盖内置命令
        self._builtin_command_classes: set[type] = set()
        # 启停配置缓存（load 开头重置，避免重复读文件）
        self._enabled_config: dict | None = None

    def load(self) -> list[Extension]:
        """执行完整加载流程：发现 -> 校验 -> 拓扑排序 -> 导入 -> 声明 -> on_load。"""
        self._builtin_command_classes.clear()
        self._enabled_config = None
        self._discover()
        self._validate_all()
        order = self._topological_sort()
        self._import_and_load(order)
        # 聚合所有扩展的 Python 依赖到 pyproject.toml 的 extensions 组
        sync_extension_dependencies()
        return self.extensions

    # ===== 发现 =====
    def _discover(self) -> None:
        """分别扫描内置扩展子目录与用户扩展目录，解析清单。"""
        for subpackage in ('Commands', 'Services'):
            self._scan_directory(BUILTIN_DIR / subpackage, builtin=True)
        if EXTENSIONS_DIR.exists():
            self._scan_directory(EXTENSIONS_DIR, builtin=False)
            return
        logger.info('用户扩展目录不存在，跳过用户扩展加载！')

    def _scan_directory(self, directory: Path, builtin: bool) -> None:
        """扫描目录下的单文件扩展与扩展目录并解析清单。"""
        for entry in directory.iterdir():
            if entry.name.startswith('.') or entry.name.startswith('_'):
                continue
            if entry.is_dir():
                self._discover_directory(entry)
            elif entry.suffix == '.py':
                self._discover_single_file(entry, builtin=builtin)

    def _discover_directory(self, directory: Path) -> None:
        """发现多文件扩展目录：读取 Extension.toml 并校验 id 与目录名一致。"""
        manifest_path = directory / MANIFEST_FILE
        if not manifest_path.exists():
            logger.warning(f'扩展目录 {directory.name} 缺少 {MANIFEST_FILE}，已跳过！')
            return
        try:
            manifest = parse_manifest(manifest_path.read_text('Utf-8'))
        except ManifestError as error:
            logger.error(f'扩展 {directory.name} 清单解析失败：{error}，已跳过！')
            return
        extension_id = manifest.extension.id
        # 校验 id 与目录名完全一致（含大小写）
        if extension_id != directory.name:
            logger.error(f'扩展 id {extension_id} 与目录名 {directory.name} 不一致，已跳过！')
            return
        enabled = self._read_enabled(directory.name)
        self._discovered[extension_id] = DiscoveredExtension(
            manifest=manifest,
            directory=directory,
            single_file=False,
            enabled=enabled,
        )
        logger.debug(f'发现扩展 {extension_id} v{manifest.extension.version}！')

    def _discover_single_file(self, file: Path, builtin: bool = False) -> None:
        """
        发现单文件扩展：导入模块读取类属性构建清单，校验 id 与文件名一致。

        内置扩展分布在 `Builtin/` 下的固定子目录（Commands/Services），
        模块 id 以子包名作前缀（如 `Commands.Bot`）；用户扩展位于 `Extensions/` 根目录，模块 id 即文件名。
        """
        extension_id = file.stem
        module_path = f'Extensions.{extension_id}'
        if builtin:
            module_path = f'Scripts.Extensions.Builtin.{file.parent.name}.{extension_id}'
        try:
            extension = self._import_single_file(module_path, extension_id)
        except Exception as error:
            logger.error(f'单文件扩展 {extension_id} 导入失败：{error}，已跳过！')
            return
        try:
            manifest = manifest_from_attributes(extension)
        except ManifestError as error:
            logger.error(f'单文件扩展 {extension_id} 元数据校验失败：{error}，已跳过！')
            return
        if manifest.extension.id != extension_id:
            logger.error(f'单文件扩展 id {manifest.extension.id} 与文件名 {extension_id} 不一致，已跳过！')
            return
        enabled = self._read_enabled(extension_id)
        self._discovered[extension_id] = DiscoveredExtension(
            manifest=manifest,
            directory=file.parent,
            single_file=True,
            enabled=enabled,
            builtin=builtin,
            module_path=module_path,
        )
        logger.debug(f'发现单文件扩展 {extension_id} v{manifest.extension.version}！')

    def _read_enabled(self, extension_id: str) -> bool:
        """读取 Config/Extensions.toml 中扩展的启停标志，缺失时默认启用。"""
        # 缓存解析结果，发现阶段多次调用时只读一次文件
        if self._enabled_config is None:
            self._enabled_config = {}
            if CONFIG_EXTENSIONS_FILE.exists():
                try:
                    self._enabled_config = tomlkit.parse(CONFIG_EXTENSIONS_FILE.read_text('Utf-8'))
                except Exception as error:
                    logger.warning(f'扩展启停配置读取失败：{error}，全部默认启用！')
        return bool(self._enabled_config.get(extension_id, {}).get('enabled', True))

    # ===== 校验 =====

    def _validate_all(self) -> None:
        """校验发现的扩展：版本兼容性、Python 依赖、入口模块命名。"""
        for extension_id, info in self._discovered.items():
            manifest = info.manifest
            try:
                self._validate_compatibility(extension_id, manifest)
                if not info.single_file:
                    # 无代码扩展包没有 __init__.py 入口，跳过入口模块校验
                    is_no_code = self._is_no_code(manifest)
                    if not is_no_code:
                        self._validate_entry_module(extension_id, info.directory)
            except (CompatibilityError, ManifestError) as error:
                # 单个扩展校验失败不阻断整体加载：标记为 blocked 并跳过导入
                info.blocked_reason = str(error)
                self._register_display(extension_id, info, ExtensionState.blocked, str(error))
                logger.error(f'校验不通过，已阻止加载：<red>{error}</red>')
                continue

    @staticmethod
    def _is_no_code(manifest: ExtensionManifest) -> bool:
        """判断清单是否为无代码扩展包（template/resources）。"""
        return bool({ExtensionType.template, ExtensionType.resources} & set(manifest.extension.types))

    def _validate_compatibility(self, extension_id: str, manifest) -> None:
        """校验扩展与当前 UniBot 版本的兼容性。"""
        constraint = manifest.compatibility.unibot
        # '*' / 空串表示任意版本（单文件扩展无 Extension.toml 时的缺省值）
        if not constraint or constraint == '*':
            return
        try:
            specifier = SpecifierSet(constraint)
        except Exception as error:
            raise CompatibilityError(f'扩展 {extension_id} 的版本约束非法：{constraint}（{error}）') from error
        current_version = get_unibot_version()
        if current_version and current_version not in specifier:
            raise CompatibilityError(f'扩展 {extension_id} 需要 UniBot {constraint}，当前为 {current_version}！')

    @staticmethod
    def _validate_entry_module(extension_id: str, directory: Path) -> None:
        """校验多文件扩展目录存在 __init__.py 入口。"""
        entry_module = directory / '__init__.py'
        if not entry_module.exists():
            raise ManifestError(f'扩展 {extension_id} 缺少入口模块 __init__.py！')

    # ===== 拓扑排序 =====

    def _topological_sort(self) -> list[str]:
        """
        建立依赖图并进行拓扑排序，检测缺失依赖与循环依赖。

        内置扩展（`builtin: 前缀声明`）优先于用户扩展排序，确保覆盖命令所需的
        内置命令类先被登记，用户扩展随后才能判定并取代内置命令。
        """
        extension_ids = set(self._discovered.keys())
        order: list[str] = []
        visited: dict[str, int] = {}  # 0=临时标记, 1=已加入

        def visit(extension_id: str, stack: list[str]) -> None:
            if visited.get(extension_id) == 1:
                return
            if visited.get(extension_id) == 0:
                cycle = ' -> '.join(stack + [extension_id])
                raise DependencyError(f'检测到循环依赖：{cycle}')
            visited[extension_id] = 0
            stack.append(extension_id)
            dependencies = self._discovered[extension_id].manifest.dependencies.extensions
            for dependency_id in dependencies:
                if dependency_id not in extension_ids:
                    raise DependencyError(f'扩展 {extension_id} 依赖缺失：{dependency_id}！')
                visit(dependency_id, stack)
            stack.pop()
            visited[extension_id] = 1
            order.append(extension_id)

        # 先访问内置扩展，确保其命令类先登记
        for extension_id in extension_ids:
            if self._discovered[extension_id].builtin:
                visit(extension_id, [])
        for extension_id in extension_ids:
            if not self._discovered[extension_id].builtin:
                visit(extension_id, [])
        return order

    # ===== 导入与加载 =====

    def _import_and_load(self, order: list[str]) -> None:
        """
        按拓扑顺序导入模块、获取扩展实例并执行声明与 on_load。

        主动禁用的扩展直接进入 `disabled`，不导入入口、不绑定、不注册。
        依赖被禁用/失败的扩展进入 `blocked`，记录阻塞原因。
        """
        blocked_reasons: dict[str, str] = {}
        for extension_id in order:
            info = self._discovered[extension_id]
            # 校验不通过（版本不兼容/入口缺失）：已登记 blocked，仅记录原因供依赖传播
            if info.blocked_reason:
                blocked_reasons[extension_id] = info.blocked_reason
                continue
            # 主动禁用：直接进入 disabled，不导入、不绑定、不注册
            if not info.enabled:
                self._register_display(extension_id, info, ExtensionState.disabled, '')
                continue
            # 图片模式未开启：渲染扩展不加载，避免 html2pic 等依赖未安装时导入失败
            if not config.image.mode and ExtensionType.renderer in info.manifest.extension.types:
                self._register_display(extension_id, info, ExtensionState.disabled, '图片模式未开启，渲染扩展不加载')
                continue
            # 无代码扩展包（template/resources）：不导入入口、无 Extension 实例
            if self._is_no_code(info.manifest):
                try:
                    self._commit_no_code_package(extension_id, info)
                except Exception as error:
                    logger.exception(f'加载无代码扩展 {extension_id} 失败！')
                    blocked_reasons[extension_id] = f'无代码扩展加载失败：{error}'
                    self._register_no_code_display(extension_id, info, ExtensionState.failed, str(error))
                    continue
                self._register_no_code_display(extension_id, info, ExtensionState.enabled, '')
                logger.success(f'加载扩展包 <yellow>{extension_id} v{info.manifest.extension.version}</yellow> 完毕！')
                continue
            # 依赖被禁用/失败：进入 blocked
            dependency_block = self._find_blocked_dependency(extension_id, blocked_reasons)
            if dependency_block is not None:
                blocked_reasons[extension_id] = dependency_block
                self._register_display(extension_id, info, ExtensionState.blocked, dependency_block)
                continue
            try:
                extension = self._import_extension(extension_id, info)
            except Exception as error:
                logger.error(f'导入扩展 {extension_id} 失败：{error}')
                blocked_reasons[extension_id] = f'导入失败：{error}'
                self._register_display(extension_id, info, ExtensionState.failed, f'导入扩展失败：{error}')
                continue
            # 两阶段绑定：一次性注入 metadata/config/data/api/logger
            try:
                self._bind(extension_id, extension, info.manifest, builtin=info.builtin)
            except Exception as error:
                extension.mark_failed(f'绑定失败：{error}')
                blocked_reasons[extension_id] = f'绑定失败：{error}'
                continue
            extension.state = ExtensionState.loaded
            # 执行声明：实例化装饰器收集的能力类并统一提交
            try:
                self._commit_services(extension)
                self._commit_commands(extension_id, extension, builtin=info.builtin)
                self._commit_renderers(extension)
            except Exception as error:
                extension.mark_failed(f'声明阶段失败：{error}')
                blocked_reasons[extension_id] = f'声明阶段失败：{error}'
                continue
            self.extensions.append(extension)
            self.manager.registry[extension_id] = extension
            logger.success(f'加载扩展 <yellow>{extension_id} v{extension.metadata.version}</yellow> 完毕！')

    def _bind(
        self,
        extension_id: str,
        extension: Extension,
        manifest: ExtensionManifest,
        *,
        builtin: bool = False,
    ) -> None:
        """
        构建作用域受限的存储与注册入口并注入到扩展实例。

        内置扩展的数据存储直接指向 `Data` 根目录；用户扩展保持在
        `Data/Exs/<id>/`（DATA_ROOT）目录式存储下，避免与运行时数据目录混淆。
        """
        assert extension.config_model is not None
        api = ServiceRegistry(self.manager)
        config_store = ExtensionConfigStore(CONFIG_ROOT, extension_id, extension.config_model)
        data_store = ExtensionDataStore(Path('Data') if builtin else DATA_ROOT / extension_id)
        extension._bind(
            api=api,
            data_store=data_store,
            config_store=config_store,
            metadata=ExtensionMetadata(manifest),
            builtin=builtin,
        )

    def _find_blocked_dependency(self, extension_id: str, blocked_reasons: dict) -> str | None:
        """查找扩展的依赖是否被禁用/失败，返回阻塞原因或 None。"""
        manifest = self._discovered[extension_id].manifest
        for dependency_id in manifest.dependencies.extensions:
            if dependency_id in blocked_reasons:
                return f'依赖扩展 {dependency_id} 不可用：{blocked_reasons[dependency_id]}'
            dep_info = self._discovered.get(dependency_id)
            if dep_info is not None and not dep_info.enabled:
                return f'依赖扩展 {dependency_id} 被禁用！'
        return None

    def _register_display(self, extension_id: str, info: DiscoveredExtension, state: ExtensionState, reason: str):
        """注册一个未绑定的展示实例（disabled/blocked），供 WebUI 展示状态。"""
        extension = Extension()
        extension._set_metadata(ExtensionMetadata(info.manifest))
        extension.state = state
        extension.builtin = info.builtin
        extension.failure_reason = reason if reason else None
        self.manager.registry[extension_id] = extension

    def _register_no_code_display(
        self,
        extension_id: str,
        info: DiscoveredExtension,
        state: ExtensionState,
        reason: str,
    ) -> None:
        """登记无代码扩展包（template/resources）的展示信息，不创建 Extension 实例。"""
        metadata = ExtensionMetadata(info.manifest)
        self.manager.no_code_info[extension_id] = {
            'id': metadata.id,
            'name': metadata.name,
            'version': metadata.version,
            'author': metadata.author,
            'description': metadata.description,
            'types': [entry.value for entry in metadata.types],
            'state': state.value,
            'failure_reason': reason if reason else None,
            'builtin': False,
            'config_schema': None,
        }

    # ===== 无代码扩展包（template/resources） =====

    def _commit_no_code_package(self, extension_id: str, info: DiscoveredExtension) -> None:
        """提交无代码扩展包：按声明类型分别注册（template 编译配置、resources 校验根目录）。"""
        manifest = info.manifest
        types = set(manifest.extension.types)
        allowed = {ExtensionType.template, ExtensionType.resources}
        if not types <= allowed:
            raise ManifestError(f'无代码扩展 {extension_id} 类型组合非法：{sorted(t.value for t in types)}！')
        if ExtensionType.template in types:
            self._commit_template_package(extension_id, info)
        if ExtensionType.resources in types:
            self._commit_resources_package(extension_id, info)

    def _commit_template_package(self, extension_id: str, info: DiscoveredExtension) -> None:
        """编译模板配置 schema、创建独立配置存储并注册 TemplateRegistration。"""
        manifest = info.manifest
        templates_dir = info.directory / manifest.template.entry
        if not templates_dir.is_dir():
            raise ManifestError(f'template 扩展 {extension_id} 入口目录 [{manifest.template.entry}] 不存在！')
        config_model = build_template_config_model(extension_id, manifest.template.config_schema)
        config_store = ExtensionConfigStore(CONFIG_ROOT, extension_id, config_model)
        registration = TemplateRegistration(
            extension_id=extension_id,
            templates_dir=templates_dir,
            resource_ids=tuple(manifest.template.resources),
            config_model=config_model,
            config_store=config_store,
        )
        self.manager.register_template(registration)

    def _commit_resources_package(self, extension_id: str, info: DiscoveredExtension) -> None:
        """校验资源根目录并注册 resources 扩展。"""
        manifest = info.manifest
        resources_root = info.directory / manifest.resources.root
        if not resources_root.is_dir():
            raise ManifestError(f'resources 扩展 {extension_id} 根目录 [{manifest.resources.root}] 不存在！')
        self.manager.register_resources(extension_id, resources_root)

    @staticmethod
    def _import_extension(extension_id: str, info: DiscoveredExtension) -> Extension:
        """导入扩展入口模块并获取 extension 实例。"""
        if info.single_file:
            return ExtensionLoader._import_single_file(info.module_path, extension_id)
        module = importlib.import_module(f'Extensions.{extension_id}')
        return ExtensionLoader._resolve_extension(module, extension_id)

    @staticmethod
    def _import_single_file(module_path: str, extension_id: str) -> Extension:
        """导入单文件扩展模块并获取 extension 实例。"""
        module = importlib.import_module(module_path)
        return ExtensionLoader._resolve_extension(module, extension_id)

    @staticmethod
    def _resolve_extension(module, extension_id: str) -> Extension:
        """从模块中解析唯一 extension 实例并校验类型。"""
        extension = getattr(module, 'extension', None)
        if extension is None:
            raise LoadError(f'扩展 {extension_id} 未导出 extension 实例！')
        if not isinstance(extension, Extension):
            raise LoadError(f'扩展 {extension_id} 的 extension 不是 Extension 子类！')
        return extension

    def _commit_services(self, extension: Extension) -> None:
        """实例化并提交装饰器声明的服务到扩展的 api 注册表。"""
        for service_cls in extension.services:
            service = service_cls()
            name = getattr(service, 'name', '') or service_cls.__name__
            extension.api.register(name, service)

    def _commit_renderers(self, extension: Extension) -> None:
        """实例化并提交装饰器声明的渲染器到全局注册表。"""
        renderer_registry = RendererRegistry(self.manager)
        for renderer_cls in extension.renderers:
            renderer_registry.register(renderer_cls())

    def _commit_commands(self, extension_id: str, extension: Extension, *, builtin: bool = False) -> None:
        for command_cls in extension.commands:
            command = command_cls()
            if builtin:
                # 记录内置命令类，供后续扩展判定是否覆盖内置
                self._builtin_command_classes.add(command_cls)
                command_manager.register_command(command, f'{BUILTIN_PREFIX}:{command.name}')
                continue
            # 扩展命令：若继承自某个内置命令类，则判定为覆盖内置，以同名
            # command_id 取代内置定义；否则作为新增命令以 extension: 前缀注册
            if builtin_cls := self._find_builtin_override(command_cls):
                command_id = f'{BUILTIN_PREFIX}:{command.name}'
                command_manager.register_command(command, command_id, override=True)
                logger.info(
                    f'扩展 {extension_id} 用 {command_cls.__name__} 覆盖内置命令 '
                    f'{builtin_cls.__name__}（{command_id}）！'
                )
                continue
            command_id = f'extension:{extension_id}:{command.name}'
            command_manager.register_command(command, command_id)

    def _find_builtin_override(self, command_cls: type) -> type | None:
        """若命令类继承自某内置命令类，返回该内置类；否则返回 None。"""
        for builtin_cls in self._builtin_command_classes:
            if command_cls is builtin_cls:
                continue
            if issubclass(command_cls, builtin_cls):
                return builtin_cls
        return None


# 供单例使用
loader = ExtensionLoader
