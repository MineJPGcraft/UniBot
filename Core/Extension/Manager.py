"""扩展管理器单例：注册表、服务、渲染器、启停状态与加载编排。"""

import asyncio
from pathlib import Path

import tomlkit

from Scripts.Config import config
from Scripts.Constants import CONFIG_EXTENSIONS_FILE
from Scripts.Logging import exception_logger, logger

from . import (
    Extension,
    ExtensionState,
)
from .Loader import (
    ExtensionLoader,
)
from .Renderer import BaseRenderer, RendererManager, TemplateRegistration


class ExtensionManager:
    """扩展管理器，负责扩展生命周期、服务注册与渲染器管理。"""

    def __init__(self) -> None:
        # 已加载扩展注册表等容器必须实例私有，避免多实例共享与热重载脏状态
        self.registry: dict[str, Extension] = {}
        self.services: dict[str, object] = {}
        self.renderers: dict[str, BaseRenderer] = {}
        # 无代码扩展包（template/resources）展示信息：extension_id -> info dict
        self.no_code_info: dict[str, dict] = {}
        self.loader = ExtensionLoader(self)
        self.renderer_manager = RendererManager(self.get_renderer)
        # 串行化热重载，防止 WebUI 与指令并发触发
        self._reload_lock = asyncio.Lock()

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
        self.registry.clear()
        self.services.clear()
        self.renderers.clear()
        self.no_code_info.clear()
        self.renderer_manager.templates.clear()
        self.renderer_manager.resources.clear()
        self.renderer_manager._environments.clear()
        self.loader.reset()

    def load(self) -> None:
        """发现、校验、排序并加载扩展（声明 + on_load），重复调用前自动重置状态。"""
        self.reset()
        self.loader.load()

    async def reload(self) -> None:
        """热重载全部扩展：停用 → 注销命令 → 清理模块缓存 → 重新加载 → 重建命令 → 重新启用。"""
        # 函数内导入：Command 模块顶层不依赖 Manager，但保持 __init__ 固定导入顺序（Base → Command → … → Manager）
        from .Command import command_manager

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
                await extension.api.enable()
                extension.transition(ExtensionState.enabled)
            except Exception as error:
                extension.mark_failed(str(error))
                await self._disable_extension(extension)
                await self._rollback(extension)
        # 图片模式开启时才初始化配置的渲染引擎；初始化失败仅降级图片功能，不阻断启动
        if config.image.mode:
            try:
                await self.renderer_manager.setup(config.image.renderer)
            except Exception as error:
                exception_logger.error(
                    f'Render engine setup failed, image output has been disabled automatically: {error}'
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

    @staticmethod
    async def _disable_extension(extension: Extension) -> None:
        """先关闭服务再释放扩展资源，清理失败不阻止后续步骤。"""
        await extension.api.disable()
        try:
            await extension.on_disable()
        except Exception as error:
            logger.error(f'Extension {extension.id} failed to shut down: {error}')

    # ===== 服务注册与获取 =====

    def register_service(self, name: str, service: object) -> None:
        """注册一个 API 服务。"""
        if name in self.services:
            logger.warning(f'API service {name} registered twice, the latest one wins.')
        self.services[name] = service

    def get_service(self, name: str) -> object | None:
        """获取已注册的 API 服务，未注册返回 None。"""
        return self.services.get(name)

    # ===== 渲染器/模板/资源管理 =====

    def register_renderer(self, renderer: BaseRenderer) -> None:
        """注册一个渲染引擎实例。"""
        if renderer.name:
            self.renderers[renderer.name] = renderer

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
        return self.renderers.get(name)

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
                'name': metadata.name,
                'version': metadata.version,
                'author': metadata.author,
                'description': metadata.description,
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
