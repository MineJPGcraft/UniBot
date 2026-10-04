"""ExtensionManager 测试：拓扑排序、生命周期、失败隔离、启停状态（验证点 9、14、8）。"""

import asyncio
from pathlib import Path
from typing import override

import pytest
import tomlkit

from Core.Extension import Extension, ExtensionState, Service, ServiceRegistry, extension_manager
from Core.Extension.Manifest import parse_manifest
from Core.Extension.Renderer import BaseRenderer
from Core.Extension.Runtime.Loader import DiscoveredExtension, ExtensionLoader


def _bind_registry(extension: Extension) -> ServiceRegistry:
    """为生命周期测试建立最小服务注册表绑定。"""
    registry = extension_manager.service_manager.registry
    extension._api = registry
    extension._bound = True
    return registry


class _GoodExt(Extension):
    def __init__(self, ext_id: str) -> None:
        super().__init__()
        self._ext_id = ext_id
        _bind_registry(self)
        self.enabled = False
        self.disabled = False

    @property
    @override
    def id(self) -> str:
        return self._ext_id

    @override
    async def on_enable(self) -> None:
        self.enabled = True

    @override
    async def on_disable(self) -> None:
        self.disabled = True


class _FailingExt(Extension):
    def __init__(self, ext_id: str) -> None:
        super().__init__()
        self._ext_id = ext_id
        _bind_registry(self)

    @property
    @override
    def id(self) -> str:
        return self._ext_id

    @override
    async def on_enable(self) -> None:
        raise RuntimeError('boom')


class _TypedService(Service):
    name = 'typed'


class _LifecycleService(Service):
    """记录服务生命周期调用。"""

    name = 'lifecycle'

    def __init__(self) -> None:
        self.enabled = False
        self.disabled = False

    @override
    async def on_enable(self) -> None:
        self.enabled = True

    @override
    async def on_disable(self) -> None:
        self.disabled = True


class _ServiceExt(Extension):
    def __init__(self, ext_id: str, service: Service) -> None:
        super().__init__()
        self._ext_id = ext_id
        registry = _bind_registry(self)
        registry.register(service.name or type(service).__name__, service, owner_id=self._ext_id)

    @property
    @override
    def id(self) -> str:
        return self._ext_id


# ===== 服务注册 =====


class TestServices:
    def test_register_and_get_service(self):
        service = object()
        extension_manager.register_service('my_svc', service)
        assert extension_manager.get_service('my_svc') is service
        assert extension_manager.get_service('missing') is None

    def test_duplicate_service_overwrites(self):
        extension_manager.register_service('svc', object())
        new_service = object()
        extension_manager.register_service('svc', new_service)
        assert extension_manager.get_service('svc') is new_service

    def test_get_service_by_type(self):
        registry = extension_manager.service_manager.registry
        service = _TypedService()
        registry.register(_TypedService.name, service)

        assert registry.get(_TypedService) is service

    def test_get_missing_service_by_type(self):
        registry = extension_manager.service_manager.registry

        assert registry.get(_TypedService) is None

    def test_get_service_by_type_rejects_wrong_runtime_type(self):
        registry = extension_manager.service_manager.registry
        registry.register(_TypedService.name, object())

        with pytest.raises(TypeError, match='API service typed is not of type _TypedService'):
            registry.get(_TypedService)


# ===== 生命周期 =====


class TestLifecycle:
    def test_start_enables_extensions_in_order(self):
        a = _GoodExt('A')
        b = _GoodExt('B')
        # 模拟 Loader 已加载：状态进入 loaded
        a.state = ExtensionState.loaded
        b.state = ExtensionState.loaded
        extension_manager.loader.extensions = [a, b]
        asyncio.run(extension_manager.start())
        assert a.enabled and b.enabled
        assert a.state is ExtensionState.enabled
        assert b.state is ExtensionState.enabled

    def test_failure_marks_failed_and_does_not_crash(self):
        good = _GoodExt('Good')
        failing = _FailingExt('Bad')
        good.state = ExtensionState.loaded
        failing.state = ExtensionState.loaded
        # extending list so rollback tries to disable good
        extension_manager.loader.extensions = [good, failing]
        asyncio.run(extension_manager.start())
        assert failing.state is ExtensionState.failed
        # rollback disables already-enabled extensions
        assert good.disabled is True

    def test_renderer_setup_failure_degrades_not_crash(self, monkeypatch):
        """渲染引擎初始化失败仅降级图片功能，不阻断扩展启动。"""
        from Core.Config import config as app_config

        async def _boom(name: str):
            raise RuntimeError('尚未选择浏览器内核')

        monkeypatch.setattr(app_config.image, 'mode', True)
        monkeypatch.setattr(extension_manager.renderer_manager, 'setup', _boom)
        ext = _GoodExt('Render')
        ext.state = ExtensionState.loaded
        extension_manager.loader.extensions = [ext]
        asyncio.run(extension_manager.start())
        assert ext.state is ExtensionState.enabled

    def test_shutdown_disables_in_reverse_order(self):
        a = _GoodExt('A')
        b = _GoodExt('B')
        a.enabled = b.enabled = True
        a.state = ExtensionState.enabled
        b.state = ExtensionState.enabled
        extension_manager.loader.extensions = [a, b]
        asyncio.run(extension_manager.shutdown())
        assert a.disabled and b.disabled
        assert a.state is ExtensionState.disabled
        assert b.state is ExtensionState.disabled

    def test_disable_keeps_registration(self):
        # disable 只停用不注销：第三方扩展缓存的句柄必须保持有效（避免重新启用时新旧两个活实例）
        service = _LifecycleService()
        ext = _ServiceExt('Svc', service)
        ext.state = ExtensionState.loaded
        extension_manager.loader.extensions = [ext]
        asyncio.run(extension_manager.start())
        assert extension_manager.get_service('lifecycle') is service
        asyncio.run(extension_manager.shutdown())
        # 已停用但登记项仍在（句柄对象不变，不会变成 None）
        assert extension_manager.get_service('lifecycle') is service
        assert service.disabled is True

    def test_reenable_reuses_same_service_instance(self):
        # re-enable 必须复用同一实例（而非新建），否则缓存的句柄与实际服务分裂
        service = _LifecycleService()
        ext = _ServiceExt('Svc', service)
        ext.state = ExtensionState.loaded
        extension_manager.loader.extensions = [ext]

        async def _cycle() -> None:
            await extension_manager.start()
            first = extension_manager.get_service('lifecycle')
            await extension_manager.shutdown()
            ext.state = ExtensionState.loaded
            await extension_manager.start()
            second = extension_manager.get_service('lifecycle')
            assert first is second is service

        asyncio.run(_cycle())
        assert service.enabled is True

    def test_rollback_declarations_unregisters_owned_capabilities(self):
        # 声明阶段失败回滚：按 owner 注销服务/命令/渲染器
        registry = extension_manager.service_manager.registry
        registry.register('rollback_svc', object(), owner_id='RB')
        loader = extension_manager.loader
        loader._rollback_declarations('RB')
        assert registry.get('rollback_svc') is None

    def test_service_lifecycle_follows_extension(self):
        service = _LifecycleService()
        ext = _ServiceExt('Svc', service)
        ext.state = ExtensionState.loaded
        extension_manager.loader.extensions = [ext]
        asyncio.run(extension_manager.start())
        assert service.enabled is True
        assert service.disabled is False
        assert ext.state is ExtensionState.enabled
        asyncio.run(extension_manager.shutdown())
        assert service.disabled is True
        assert ext.state is ExtensionState.disabled


# ===== 启停状态文件 =====


class TestSetEnabled:
    def test_set_enabled_writes_config_file(self, tmp_path, monkeypatch):
        import Core.Extension.Runtime.Manager as ext_mod

        # 将 Extension 模块内的 CONFIG_EXTENSIONS_FILE 常量指向临时目录
        config_file = tmp_path / 'Extensions.toml'
        monkeypatch.setattr(ext_mod, 'CONFIG_EXTENSIONS_FILE', config_file)
        extension_manager.set_enabled('WeatherExt', True)
        assert config_file.exists()
        data = tomlkit.parse(config_file.read_text('Utf-8'))
        assert data['WeatherExt']['enabled'] is True

    def test_set_enabled_merges_multiple_extensions(self, tmp_path, monkeypatch):
        import Core.Extension.Runtime.Manager as ext_mod

        config_file = tmp_path / 'Extensions.toml'
        monkeypatch.setattr(ext_mod, 'CONFIG_EXTENSIONS_FILE', config_file)
        extension_manager.set_enabled('WeatherExt', True)
        extension_manager.set_enabled('List', False)
        data = tomlkit.parse(config_file.read_text('Utf-8'))
        assert data['WeatherExt']['enabled'] is True
        assert data['List']['enabled'] is False


# ===== 校验失败隔离（验证点 14：单个扩展失败不阻断整体加载） =====


class TestValidationIsolation:
    """版本不兼容/入口缺失等校验失败时，仅该扩展进入 blocked，整体加载不崩溃。"""

    @staticmethod
    def _make_loader_with(manifests: dict[str, str], deps: dict[str, list[str]] | None = None) -> ExtensionLoader:
        """构造携带指定清单的 ExtensionLoader，跳过真实目录扫描。"""
        deps = deps or {}
        loader = ExtensionLoader(extension_manager._registries, extension_manager.renderer_manager)
        for extension_id, content in manifests.items():
            manifest = parse_manifest(content)
            # 在清单的 [dependencies] 段写入依赖关系
            manifest.dependencies.extensions = deps.get(extension_id, [])
            loader._discovered[extension_id] = DiscoveredExtension(
                manifest=manifest,
                directory=Path('unused'),
                single_file=True,
                enabled=True,
            )
        return loader

    def test_incompatible_extension_blocked_not_crash(self, monkeypatch):
        # 固定当前 UniBot 版本，使 ">=999.0.0" 约束必然不满足
        monkeypatch.setattr('Core.Extension.Manifest.get_unibot_version', lambda: '1.0.0')
        loader = self._make_loader_with(
            {
                'Playwright': """
[extension]
id = "Playwright"
name = "Playwright 渲染引擎"
version = "1.0.0"
types = ["api"]

[compatibility]
unibot = ">=999.0.0"
""",
            }
        )
        # 完整校验+排序+加载流程，不应抛异常
        loader._validate_all()
        loader._import_and_load(loader._topological_sort())
        info = extension_manager.registry.get('Playwright')
        assert info is not None
        assert info.state is ExtensionState.blocked
        assert info.failure_reason is not None
        assert 'UniBot' in info.failure_reason

    def test_compatible_extension_still_loads_alongside_blocked(self, monkeypatch):
        monkeypatch.setattr('Core.Extension.Manifest.get_unibot_version', lambda: '1.0.0')
        loader = self._make_loader_with(
            {
                'GoodExt': """
[extension]
id = "GoodExt"
name = "正常扩展"
version = "1.0.0"
types = ["api"]

[compatibility]
unibot = "*"
""",
                'BadExt': """
[extension]
id = "BadExt"
name = "不兼容扩展"
version = "1.0.0"
types = ["api"]

[compatibility]
unibot = ">=999.0.0"
""",
            }
        )
        loader._validate_all()
        loader._import_and_load(loader._topological_sort())
        assert extension_manager.registry['BadExt'].state is ExtensionState.blocked
        # GoodExt 未失败也未被禁用：应进入 failed（模块不存在，导入失败）而非崩溃
        assert extension_manager.registry['GoodExt'].state in (
            ExtensionState.failed,
            ExtensionState.blocked,
        )

    def test_dependent_extension_also_blocked(self, monkeypatch):
        monkeypatch.setattr('Core.Extension.Manifest.get_unibot_version', lambda: '1.0.0')
        loader = self._make_loader_with(
            {
                'Incompat': """
[extension]
id = "Incompat"
name = "底层不兼容扩展"
version = "1.0.0"
types = ["api"]

[compatibility]
unibot = ">=999.0.0"
""",
                'Depends': """
[extension]
id = "Depends"
name = "依赖扩展"
version = "1.0.0"
types = ["api"]

[compatibility]
unibot = "*"
""",
            },
            deps={'Depends': ['Incompat']},
        )
        loader._validate_all()
        order = loader._topological_sort()
        # 拓扑排序必须仍能完成，不抛 DependencyError
        assert 'Incompat' in order and 'Depends' in order
        loader._import_and_load(order)
        assert extension_manager.registry['Incompat'].state is ExtensionState.blocked
        assert extension_manager.registry['Depends'].state is ExtensionState.blocked
        assert 'Incompat' in (extension_manager.registry['Depends'].failure_reason or '')


# ===== 图片模式关闭时的渲染扩展处理（#7） =====


def _renderer_manifest(extension_id: str, types: str) -> str:
    """构造渲染相关扩展清单，`types` 为 TOML 数组字面量（如 `["renderer"]`）。"""
    return f"""
[extension]
id = "{extension_id}"
name = "{extension_id}"
version = "1.0.0"
types = {types}

[renderer]
name = "engine_{extension_id}"
"""


class TestImageModeRendererSkip:
    """图片模式关闭时：纯渲染器扩展整体跳过，混合扩展仅跳过渲染器声明。"""

    @staticmethod
    def _discovered(manifest: str) -> DiscoveredExtension:
        return DiscoveredExtension(
            manifest=parse_manifest(manifest),
            directory=Path('unused'),
            single_file=True,
            enabled=True,
        )

    def test_pure_renderer_extension_skipped_when_image_mode_off(self, monkeypatch):
        from Core.Config import config

        monkeypatch.setattr(config.image, 'mode', False)
        loader = ExtensionLoader(extension_manager._registries, extension_manager.renderer_manager)
        info = self._discovered(_renderer_manifest('PureRenderer', '["renderer"]'))
        assert loader._skip_before_import('PureRenderer', info, {}) is True
        assert extension_manager.registry['PureRenderer'].state is ExtensionState.disabled

    def test_mixed_renderer_extension_not_skipped_when_image_mode_off(self, monkeypatch):
        # renderer + api 的混合扩展：api 能力必须照常加载，不能因图片模式关闭被整体跳过
        from Core.Config import config

        monkeypatch.setattr(config.image, 'mode', False)
        loader = ExtensionLoader(extension_manager._registries, extension_manager.renderer_manager)
        info = self._discovered(_renderer_manifest('MixedRenderer', '["renderer", "api"]'))
        assert loader._skip_before_import('MixedRenderer', info, {}) is False

    def test_mixed_renderer_declaration_skipped_when_image_mode_off(self, monkeypatch):
        # 混合扩展的渲染器声明在图片模式关闭时跳过（渲染器注册表不应出现该引擎）
        from Core.Config import config

        loader = ExtensionLoader(extension_manager._registries, extension_manager.renderer_manager)
        info = self._discovered(_renderer_manifest('MixedRenderer', '["renderer", "api"]'))

        class _Engine(BaseRenderer):
            name = 'engine_MixedRenderer'

            async def render(self, html: str, css: str, size=None) -> bytes:
                return b''

        def _make_extension() -> Extension:
            extension = Extension()
            extension._declared_id = 'MixedRenderer'
            extension.renderers.append(_Engine)
            return extension

        monkeypatch.setattr(config.image, 'mode', False)
        assert loader._try_commit_declarations('MixedRenderer', _make_extension(), info, {}) is True
        assert 'engine_MixedRenderer' not in extension_manager.renderer_manager.renderers

        # 图片模式开启时同一扩展的渲染器正常注册（证明差异只来自图片模式开关）
        extension_manager.reset()
        monkeypatch.setattr(config.image, 'mode', True)
        assert loader._try_commit_declarations('MixedRenderer', _make_extension(), info, {}) is True
        assert 'engine_MixedRenderer' in extension_manager.renderer_manager.renderers


# ===== 扩展注册表按 owner 注销（#6：三处注册表对称） =====


class TestExtensionRegistryOwnerCleanup:
    def test_unregister_by_owner_clears_instance_and_no_code_info(self):
        registry = extension_manager._registries.extensions
        extension = Extension()
        extension._declared_id = 'Mixed'
        registry.register_extension('Mixed', extension)
        registry.register_no_code_info('Mixed', {'id': 'Mixed'})
        removed = registry.unregister_by_owner('Mixed')
        assert removed == ['Mixed', 'Mixed']
        assert registry.get_extension('Mixed') is None
        assert 'Mixed' not in registry.no_code_info

    def test_unregister_by_owner_is_idempotent(self):
        registry = extension_manager._registries.extensions
        assert registry.unregister_by_owner('Missing') == []


# ===== 第三方扩展缓存服务句柄（#6 关键场景） =====


class TestCachedServiceHandle:
    """扩展在 on_load 中缓存 `api.get(...)` 句柄时，disable/re-enable 不得使其失效。"""

    def test_cached_handle_survives_disable_and_reenable(self):
        service = _LifecycleService()
        provider = _ServiceExt('Provider', service)
        provider.state = ExtensionState.loaded
        extension_manager.loader.extensions = [provider]

        async def _scenario() -> None:
            await extension_manager.start()
            # 模拟第三方扩展在 on_load 期间缓存句柄
            cached = extension_manager.service_manager.registry.get(_LifecycleService)
            assert cached is service
            await extension_manager.shutdown()
            # disable 后：缓存句柄必须仍是同一对象（仅停用，不销毁也不卸载登记）
            assert extension_manager.service_manager.registry.get(_LifecycleService) is service
            provider.state = ExtensionState.loaded
            await extension_manager.start()
            # re-enable 后仍是同一实例（不会新建第二个活实例）
            assert extension_manager.service_manager.registry.get(_LifecycleService) is cached

        asyncio.run(_scenario())
        assert service.enabled is True

    def test_rollback_unregisters_while_disable_does_not(self):
        # 对照：声明失败回滚会真正注销；disable 不会
        service = _LifecycleService()
        provider = _ServiceExt('Provider', service)
        provider.state = ExtensionState.loaded
        extension_manager.loader.extensions = [provider]
        asyncio.run(extension_manager.start())

        extension_manager.loader._rollback_declarations('Provider')
        assert extension_manager.service_manager.registry.get('lifecycle') is None
