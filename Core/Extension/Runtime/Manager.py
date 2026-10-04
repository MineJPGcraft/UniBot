"""
扩展管理器单例：生命周期编排、热重载、启停状态与展示信息。

本模块是运行时引擎的**顶层组合器**：创建 `ExtensionRegistries` 容器集合，
并把容器与 `RendererManager` 按引用交给 `ExtensionLoader`，因此位于 `Runtime/`
根（而非 `Managers/` 子包）——否则会与 `Loader.py` 形成循环导入。

注册状态全部委托给 `Registries/` 容器：扩展本体与无代码包展示信息在
`ExtensionRegistry`，服务在 `ServiceRegistry`，渲染器/模板/资源在
`RendererManager` 持有的三个容器中；命令注册表由全局 `command_manager` 自持。
"""

import asyncio
from pathlib import Path

import tomlkit

from Core.Config import config
from Core.Constants import CONFIG_EXTENSIONS_FILE
from Core.Logging import exception_logger, logger

from ..Extension import Extension, ExtensionState
from ..Renderer import BaseRenderer, TemplateRegistration
from .Loader import ExtensionLoader
from .Managers import RendererManager, ServiceManager, command_manager
from .Registries import ExtensionRegistries


class ExtensionManager:
    """扩展管理器，负责扩展生命周期、服务注册与渲染器管理。"""

    def __init__(self) -> None:
        # 注册容器与加载状态必须实例私有，避免多实例共享与热重载脏状态
        self._registries = ExtensionRegistries()
        self.service_manager = ServiceManager(self._registries.services)
        self.renderer_manager = RendererManager(
            self._registries.renderers,
            self._registries.templates,
            self._registries.resources,
        )
        # 注册容器与渲染管理器按引用交给 Loader，避免回调注入
        self.loader = ExtensionLoader(self._registries, self.renderer_manager)
        # 串行化热重载，防止 WebUI 与指令并发触发
        self._reload_lock = asyncio.Lock()

    @property
    def registry(self) -> dict[str, Extension]:
        """已加载扩展注册表：id -> Extension。"""
        return self._registries.extensions.extensions

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
        """无代码扩展包展示信息：extension_id -> info dict。"""
        return self._registries.extensions.no_code_info

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
        self.renderer_manager.reset()
        self.loader.reset()

    def load(self) -> None:
        """
        发现、校验、排序并加载扩展（声明 + on_load）。

            内部先 reset 状态；已绑定实例（模块缓存未清理时）会被复用并重新提交声明，
            不会重复绑定。注意：本方法不清理已构建的命令 matcher——若此前调用过
            `command_manager.build()`，重复 `load()` 会因命令管理器已构建而拒绝注册；
            完整热重载请用 `reload()`（含 matcher 注销与模块缓存清理）。
        """
        self.reset()
        self.loader.load()

    async def reload(self) -> None:
        """热重载全部扩展：停用 → 注销命令 → 清理模块缓存 → 重新加载 → 重建命令 → 重新启用。"""
        async with self._reload_lock:
            if failed := self.loader.check_syntax():
                raise RuntimeError(f'Extension syntax check failed: {", ".join(failed)}')
            logger.info('Reloading all extensions...')
            await self.shutdown()
            command_manager.cleanup_matchers()
            self.loader.purge_modules()
            self.load()
            command_manager.build()
            await self.start()
            logger.success('All extensions reloaded.')

    async def start(self) -> None:
        """按拓扑顺序调用 on_load 与 on_enable，失败时回滚已启用扩展；渲染引擎失败仅降级图片功能。"""
        for extension in self.loader.extensions:
            if extension.state is not ExtensionState.loaded:
                continue
            try:
                await extension.on_load()
                await extension.on_enable()
                await self.service_manager.enable(extension.id)
                extension.transition(ExtensionState.enabled)
            except Exception as error:
                extension.mark_failed(str(error))
                await self._disable_extension(extension)
                await self._rollback(extension)
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

    async def _rollback(self, failed_extension: Extension) -> None:
        """当某个扩展启用失败时，按逆拓扑顺序回滚已启用扩展。"""
        for extension in reversed(self.loader.extensions):
            if extension is failed_extension:
                continue
            if extension.state is ExtensionState.enabled:
                await self._disable_extension(extension)
                extension.transition(ExtensionState.disabled)

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

    # ===== 注册透传（供 Loader / 测试直接登记） =====

    def register_extension(self, extension_id: str, extension: Extension) -> None:
        """登记一个已加载的扩展实例。"""
        self._registries.extensions.register_extension(extension_id, extension)

    def register_no_code_info(self, extension_id: str, info: dict) -> None:
        """登记一个无代码扩展包（template/resources）的展示信息。"""
        self._registries.extensions.register_no_code_info(extension_id, info)

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
        config_path.write_text(tomlkit.dumps(data), encoding='Utf-8')
        logger.info(
            f'Extension {extension_id} set to {"enabled" if enabled else "disabled"}, takes effect after restart.'
        )

    # ===== 展示信息 =====

    def get_extension_info(self, extension_id: str) -> dict:
        """获取扩展的展示信息（供 WebUI 使用）。"""
        extension = self.registry.get(extension_id)
        if extension is not None:
            metadata = extension.metadata
            return {
                'id': metadata.id,
                'name': str(metadata.name),
                'version': metadata.version,
                'author': metadata.author,
                'description': str(metadata.description),
                'types': [entry.value for entry in metadata.types],
                'state': extension.state.value,
                'failure_reason': extension.failure_reason,
                'builtin': extension.builtin,
                'config_schema': extension.get_config_schema(),
            }
        # 无代码扩展包（template/resources）：无 Extension 实例，信息由 Loader 提交
        info = self.no_code_info.get(extension_id)
        if info is None:
            return {}
        registration = self.renderer_manager.templates.get(extension_id)
        if registration is not None:
            info['config_schema'] = registration.config_model.model_json_schema()
        return dict(info)

    def get_extensions(self) -> list[dict]:
        """获取全部已加载扩展的展示信息（代码扩展 + 无代码扩展包）。"""
        ids = list(self.registry) + [eid for eid in self.no_code_info if eid not in self.registry]
        return [self.get_extension_info(extension_id) for extension_id in ids]


# 单例
extension_manager = ExtensionManager()
