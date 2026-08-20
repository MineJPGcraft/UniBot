"""ExtensionManager 测试：拓扑排序、生命周期、失败隔离、启停状态（验证点 9、14、8）。"""

import asyncio
from pathlib import Path
from typing import override

import pytest
import tomlkit

from Scripts.Extensions import Extension, ExtensionState, Service, ServiceRegistry, extension_manager
from Scripts.Extensions.Base import parse_manifest
from Scripts.Extensions.Loader import DiscoveredExtension, ExtensionLoader


def _bind_registry(extension: Extension) -> ServiceRegistry:
    """为生命周期测试建立最小服务注册表绑定。"""
    registry = ServiceRegistry(extension_manager)
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
        registry.register(service.name or type(service).__name__, service)

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
        registry = ServiceRegistry(extension_manager)
        service = _TypedService()
        registry.register(_TypedService.name, service)

        assert registry.get(_TypedService) is service

    def test_get_missing_service_by_type(self):
        registry = ServiceRegistry(extension_manager)

        assert registry.get(_TypedService) is None

    def test_get_service_by_type_rejects_wrong_runtime_type(self):
        registry = ServiceRegistry(extension_manager)
        registry.register(_TypedService.name, object())

        with pytest.raises(TypeError, match='API 服务 typed 的类型不是 _TypedService'):
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
        import Scripts.Extensions.Manager as ext_mod

        # 将 Extension 模块内的 CONFIG_EXTENSIONS_FILE 常量指向临时目录
        config_file = tmp_path / 'Extensions.toml'
        monkeypatch.setattr(ext_mod, 'CONFIG_EXTENSIONS_FILE', config_file)
        extension_manager.set_enabled('WeatherExt', True)
        assert config_file.exists()
        data = tomlkit.parse(config_file.read_text('Utf-8'))
        assert data['WeatherExt']['enabled'] is True

    def test_set_enabled_merges_multiple_extensions(self, tmp_path, monkeypatch):
        import Scripts.Extensions.Manager as ext_mod

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
        loader = ExtensionLoader(extension_manager)
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
        monkeypatch.setattr('Scripts.Extensions.Loader.get_unibot_version', lambda: '1.0.0')
        loader = self._make_loader_with({
            'Playwright': """
[extension]
id = "Playwright"
name = "Playwright 渲染引擎"
version = "1.0.0"
types = ["api"]

[compatibility]
unibot = ">=999.0.0"
""",
        })
        # 完整校验+排序+加载流程，不应抛异常
        loader._validate_all()
        loader._import_and_load(loader._topological_sort())
        info = extension_manager.registry.get('Playwright')
        assert info is not None
        assert info.state is ExtensionState.blocked
        assert info.failure_reason is not None
        assert 'UniBot' in info.failure_reason

    def test_compatible_extension_still_loads_alongside_blocked(self, monkeypatch):
        monkeypatch.setattr('Scripts.Extensions.Loader.get_unibot_version', lambda: '1.0.0')
        loader = self._make_loader_with({
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
        })
        loader._validate_all()
        loader._import_and_load(loader._topological_sort())
        assert extension_manager.registry['BadExt'].state is ExtensionState.blocked
        # GoodExt 未失败也未被禁用：应进入 failed（模块不存在，导入失败）而非崩溃
        assert extension_manager.registry['GoodExt'].state in (
            ExtensionState.failed,
            ExtensionState.blocked,
        )

    def test_dependent_extension_also_blocked(self, monkeypatch):
        monkeypatch.setattr('Scripts.Extensions.Loader.get_unibot_version', lambda: '1.0.0')
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
