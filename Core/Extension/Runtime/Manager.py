"""
扩展管理器单例：生命周期编排、热重载、启停状态与展示信息。

本模块是运行时引擎的**顶层组合器**：创建 `ExtensionRegistries` 容器集合，
并把容器与 `RendererManager` 按引用交给 `ExtensionLoader`，因此位于 `Runtime/`
根（而非 `Managers/` 子包）——否则会与 `Loader.py` 形成循环导入。

注册状态全部委托给 `Registries/` 容器：扩展本体与无代码包展示信息在
`ExtensionRegistry`，服务、命令、渲染器、模板与资源分别在各自的纯容器中，
由 `ServiceManager` / `CommandManager` / `RendererManager` 按引用持有。
"""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import tomlkit

from Core.Config import config
from Core.Constants import CONFIG_EXTENSIONS_FILE
from Core.Files import atomic_write
from Core.Logging import exception_logger, logger

from ..Errors import LoadError
from ..Extension import Extension, ExtensionState
from ..Manifest import _CODE_TYPES
from ..Renderer import BaseRenderer, TemplateRegistration
from .Loader import ExtensionLoader
from .Managers import CommandManager, RendererManager, ServiceManager
from .Registries import ExtensionRecord, ExtensionRegistries


@dataclass
class ReloadResult:
    """热重载结果：失败阶段、失败扩展与是否已恢复旧状态。"""

    success: bool
    failed_stage: str = ''
    error: str = ''
    recovered: bool = False


class ExtensionManager:
    """扩展管理器，负责扩展生命周期、服务注册与渲染器管理。"""

    def __init__(self) -> None:
        # 注册容器与加载状态必须实例私有，避免多实例共享与热重载脏状态
        self._registries = ExtensionRegistries()
        self.service_manager = ServiceManager(self._registries.services)
        self.command_manager = CommandManager(self._registries.commands, self._registries.extensions)
        self.renderer_manager = RendererManager(
            self._registries.renderers,
            self._registries.templates,
            self._registries.resources,
        )
        # 注册容器与渲染/命令管理器按引用交给 Loader，避免回调注入
        self.loader = ExtensionLoader(self._registries, self.renderer_manager, self.command_manager)
        # 串行化热重载，防止 WebUI 与指令并发触发
        self._reload_lock = asyncio.Lock()

    @property
    def registry(self) -> dict[str, Extension]:
        """已加载扩展注册表：id -> Extension。"""
        return self._registries.extensions.extensions

    @property
    def records(self) -> dict[str, ExtensionRecord]:
        """全部已发现扩展的运行记录，代码实例可选。"""
        return dict(self._registries.extensions.records)

    @property
    def services(self) -> dict[str, object]:
        """已注册的 API 服务表：name -> service。"""
        return self._registries.services.all()

    @property
    def renderers(self) -> dict[str, BaseRenderer]:
        """已注册的渲染引擎表：name -> BaseRenderer。"""
        return self.renderer_manager.renderers

    @property
    def no_code_info(self) -> dict[str, dict]:
        """从运行记录生成无代码包信息，保留既有查询接口。"""
        return {
            key: self.get_extension_info(key) for key, record in self.records.items()
            if record.metadata is not None and not (_CODE_TYPES & set(record.metadata.types))
        }

    @property
    def templates(self) -> dict[str, TemplateRegistration]:
        """已注册的 template 扩展包：id -> TemplateRegistration。"""
        return self.renderer_manager.templates

    @property
    def resources(self) -> dict[str, Path]:
        """已注册的 resources 扩展包：id -> 资源根目录。"""
        return self.renderer_manager.resources

    # ===== 加载与生命周期 =====

    def reset(self) -> None:
        """清空全部注册与加载状态（重新加载前调用，测试也用它做隔离）。"""
        self._registries.extensions.clear()
        self._registries.services.clear()
        self.service_manager.clear()
        self.command_manager.clear()
        self.renderer_manager.reset()
        self.loader.reset()

    def load(self) -> None:
        """
        发现、校验、排序并加载扩展（声明 + on_load）。

            内部先 reset 状态；已绑定实例（模块缓存未清理时）会被复用并重新提交声明，
            不会重复绑定。注意：本方法不清理已构建的命令 matcher——若此前调用过
            `self.command_manager.build()`，重复 `load()` 会因命令管理器已构建而拒绝注册；
            完整热重载请用 `reload()`（含 matcher 注销与模块缓存清理）。
        """
        self.reset()
        self.loader.load()

    async def reload(self) -> ReloadResult:
        """
        热重载全部扩展：停用 → 注销命令 → 清理模块缓存 → 重新加载 → 重建命令 → 重新启用。

            语法预检失败时早退、保持旧状态（不破坏现场）。切换到候选状态的过程中
            任一阶段（加载 / 命令构建 / 启用）失败，会尝试恢复旧扩展模块缓存并重新加载，
            返回结构化 `ReloadResult`（失败阶段、错误、是否已恢复），而不是直接抛异常。
        """
        async with self._reload_lock:
            if failed := self.loader.check_syntax():
                # 语法错误文本含 `(<unknown>, line N)`，须转义尖括号避免被 loguru 当作颜色标签
                detail = f'Extension syntax check failed: {", ".join(failed)}'
                logger.error(detail.replace('<', '\\<'))
                return ReloadResult(success=False, failed_stage='syntax', error=detail, recovered=True)
            logger.info('Reloading all extensions...')
            old_modules = self._snapshot_modules()
            await self.shutdown()
            self.command_manager.cleanup_matchers()
            self.loader.purge_modules()
            return await self._switch_to_candidate(old_modules)

    async def _switch_to_candidate(self, old_modules: dict[str, ModuleType]) -> ReloadResult:
        """加载候选状态并启用；失败时恢复旧模块并尝试回到旧状态。"""
        stage = 'load'
        try:
            self.load()
            self._raise_on_failed_extensions()
            stage = 'build'
            self.command_manager.build()
            stage = 'start'
            await self.start()
            self._raise_on_failed_extensions()
        except Exception as error:
            exception_logger.error(f'Extension reload failed during {stage}: {error}')
            recovered = await self._recover(old_modules)
            return ReloadResult(success=False, failed_stage=stage, error=str(error), recovered=recovered)
        logger.success('All extensions reloaded.')
        return ReloadResult(success=True)

    def _snapshot_modules(self) -> dict[str, ModuleType]:
        """快照扩展相关模块对象，供切换失败时恢复旧代码。"""
        return {
            name: module
            for name, module in sys.modules.items()
            if name.startswith('Extensions.') or name == 'Core.Builtin' or name.startswith('Core.Builtin.')
        }

    async def _recover(self, old_modules: dict[str, ModuleType]) -> bool:
        """
        恢复旧扩展状态：还原模块缓存 → 清理候选模块 → 重新加载 → 重建命令 → 重新启用。

            尽力而为：受 NoneBot/Alconna 全局注册限制，恢复过程本身也可能失败，
            失败时返回 False，调用方据此提示需要手动处理。
        """
        try:
            await self.shutdown()
            self.command_manager.cleanup_matchers()
            self.loader.purge_modules()
            sys.modules.update(old_modules)
            self.load()
            self._raise_on_failed_extensions()
            self.command_manager.build()
            await self.start()
            self._raise_on_failed_extensions()
        except Exception as error:
            exception_logger.error(f'Failed to recover previous extension state: {error}')
            return False
        logger.warning('Reload failed; the previous extension state has been restored.')
        return True

    def _raise_on_failed_extensions(self) -> None:
        failures = [
            f'{info["id"]}: {info["failure_reason"] or info["state"]}'
            for info in self.get_extensions()
            if info['state'] == ExtensionState.failed
        ]
        failures.extend(f'{extension_id}: {reason}' for extension_id, reason in self.loader.failures.items())
        if failures:
            raise LoadError('; '.join(failures))

    async def start(self) -> None:
        """按依赖顺序启用扩展，失败仅清理自身并阻塞依赖方。"""
        discovered = bool(self.loader.load_order)
        extension_order = self.loader.load_order if discovered else [
            extension.id for extension in self.loader.extensions
        ]
        loaded_extensions = {extension.id: extension for extension in self.loader.extensions}
        for extension_id in extension_order:
            record = self._registries.extensions.records.get(extension_id)
            if record is None and not discovered:
                extension = loaded_extensions.get(extension_id)
                if extension is None:
                    continue
            elif record is None or record.instance is None:
                self._block_unavailable_record(extension_id, record)
                continue
            else:
                extension = record.instance
            if extension.state is not ExtensionState.loaded:
                continue
            if reason := self._unavailable_dependency(extension):
                extension.failure_reason = reason
                extension.transition(ExtensionState.blocked)
                continue
            try:
                await extension.on_load()
                await extension.on_enable()
                await self.service_manager.enable(extension.id)
                extension.transition(ExtensionState.enabled)
            except Exception as error:
                extension.mark_failed(str(error))
                await self._disable_extension(extension)
        # 图片模式开启时才预初始化配置的渲染引擎；未配置时延迟到渲染时按模板协商。
        # 初始化失败不阻断启动：渲染时会重新尝试并按模板声明协商降级
        if config.image.mode and config.image.renderer:
            try:
                await self.renderer_manager.setup(config.image.renderer)
            except Exception as error:
                exception_logger.error(
                    f'Render engine setup failed, render engine will be negotiated at render time: {error}'
                )
        logger.success('All extensions started.')

    def _unavailable_dependency(self, extension: Extension) -> str:
        if extension._metadata is None:
            return ''
        for dependency_id in extension.metadata.extension_dependencies:
            info = self.get_extension_info(dependency_id)
            if not info or info['state'] != ExtensionState.enabled:
                return f'依赖扩展 {dependency_id} 未启用'
        return ''

    def _block_unavailable_record(self, extension_id: str, record: ExtensionRecord | None) -> None:
        if record is None or record.metadata is None or record.state is not ExtensionState.enabled:
            return
        for dependency_id in record.metadata.extension_dependencies:
            dependency = self._registries.extensions.records.get(dependency_id)
            if dependency is not None and dependency.state is ExtensionState.enabled:
                continue
            record._failure_reason = f'依赖扩展 {dependency_id} 未启用'
            record._state = ExtensionState.blocked
            self.renderer_manager.unregister_template(extension_id)
            self.renderer_manager.unregister_resources(extension_id)
            self.renderer_manager.unregister_renderers_by_owner(extension_id)
            self.renderer_manager.invalidate_all()
            return

    async def shutdown(self) -> None:
        """按逆拓扑顺序释放资源，单个扩展失败不阻止其它扩展关闭。"""
        for extension in reversed(self.loader.extensions):
            if extension.state is not ExtensionState.enabled:
                continue
            await self._disable_extension(extension)
            extension.transition(ExtensionState.disabled)
        await self.renderer_manager.shutdown()

    async def _disable_extension(self, extension: Extension) -> None:
        """先关闭服务再释放扩展资源，清理失败不阻止后续步骤。"""
        await self.service_manager.disable(extension.id)
        try:
            await extension.on_disable()
        except Exception as error:
            logger.error(f'Extension {extension.id} failed to shut down: {error}')

    # ===== 注册透传（供测试直接登记能力） =====

    def register_service(self, name: str, service: object, *, owner_id: str = '') -> None:
        """注册一个 API 服务，`owner_id` 声明归属扩展。"""
        self._registries.services.register(name, service, owner_id=owner_id)

    def get_service(self, name: str) -> object | None:
        """获取已注册的 API 服务，未注册返回 None。"""
        return self._registries.services.get(name)

    # ===== 渲染器/模板/资源管理 =====

    def register_renderer(self, renderer: BaseRenderer) -> None:
        """注册一个渲染引擎实例。"""
        self.renderer_manager.register(renderer)

    def register_template(self, registration: TemplateRegistration) -> None:
        """注册 template 无代码扩展包。"""
        self.renderer_manager.register_template(registration)

    def unregister_template(self, extension_id: str) -> None:
        """注销 template 无代码扩展包。"""
        self.renderer_manager.unregister_template(extension_id)

    def register_resources(self, extension_id: str, resources_dir: Path) -> None:
        """注册 resources 无代码扩展包。"""
        self.renderer_manager.register_resources(extension_id, resources_dir)

    def unregister_resources(self, extension_id: str) -> None:
        """注销 resources 无代码扩展包。"""
        self.renderer_manager.unregister_resources(extension_id)

    def get_renderer(self, name: str) -> BaseRenderer | None:
        """获取指定名称的渲染引擎实例。"""
        return self.renderer_manager.get_renderer(name)

    # ===== 启停状态 =====

    def set_enabled(self, extension_id: str, enabled: bool) -> None:
        """设置扩展启停状态（写入 Config/Extensions.toml，重启生效）。"""
        config_path = CONFIG_EXTENSIONS_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if config_path.exists():
            try:
                data = tomlkit.parse(config_path.read_text('Utf-8'))
            except Exception:
                data = {}
        extension_config = dict(data.get(extension_id, {}))
        extension_config['enabled'] = enabled
        data[extension_id] = extension_config
        atomic_write(config_path, tomlkit.dumps(data))
        logger.info(
            f'Extension <blue>{extension_id}</blue> set to {"enabled" if enabled else "disabled"}, '
            'takes effect after restart.'
        )

    # ===== 展示信息 =====

    def get_extension_info(self, extension_id: str) -> dict:
        """获取扩展的展示信息（供 WebUI 使用）。"""
        record = self._registries.extensions.records.get(extension_id)
        if record is None or record.metadata is None:
            return {}
        metadata = record.metadata
        schema = record.instance.get_config_schema() if record.instance is not None else None
        registration = self.renderer_manager.templates.get(extension_id)
        if schema is None and registration is not None:
            schema = registration.config_model.model_json_schema()
        return {
            'id': metadata.id,
            'name': str(metadata.name),
            'version': metadata.version,
            'author': metadata.author,
            'description': str(metadata.description),
            'types': [entry.value for entry in metadata.types],
            'state': record.state.value,
            'failure_reason': record.failure_reason,
            'builtin': record.builtin,
            'config_schema': schema,
        }

    def get_extensions(self) -> list[dict]:
        """获取全部已加载扩展的展示信息（代码扩展 + 无代码扩展包）。"""
        return [self.get_extension_info(extension_id) for extension_id in self.records]


# 单例
extension_manager = ExtensionManager()
