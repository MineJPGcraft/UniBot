"""渲染扩展测试（A4）：渲染器注册、RendererManager 激活/回退/清理、模板/资源注册。"""

import asyncio
from pathlib import Path

import pytest

from Scripts.Extensions import BaseRenderer, RendererManager, extension_manager
from Scripts.Extensions.Loader import CONFIG_ROOT
from Scripts.Extensions.Renderer import (
    FileAsset,
    OnlineAsset,
    TemplateRegistration,
    build_template_config_model,
)
from Scripts.Extensions.Storage import ExtensionConfigStore


class _FakeRenderer(BaseRenderer):
    def __init__(self, name: str) -> None:
        self.name = name
        self.setup_called = False
        self.shutdown_called = False
        self.rendered = []

    async def setup(self) -> None:
        self.setup_called = True

    async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        self.rendered.append((html, css))
        return f'{self.name}:{html}:{css}'.encode()

    async def shutdown(self) -> None:
        self.shutdown_called = True


# ===== 渲染器注册 =====


class TestRendererRegistration:
    def test_register_and_get_renderer(self):
        renderer = _FakeRenderer('fake')
        extension_manager.register_renderer(renderer)
        assert extension_manager.get_renderer('fake') is renderer
        assert extension_manager.get_renderer('missing') is None

    def test_register_without_name_is_ignored(self):
        class _NoName(BaseRenderer):
            async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
                return b''

        extension_manager.register_renderer(_NoName())
        assert extension_manager.renderers == {}

    def test_register_template(self):
        extension_manager.register_renderer(_FakeRenderer('x'))
        model = build_template_config_model('T', {})
        store = ExtensionConfigStore(Path(CONFIG_ROOT), 'T', model)
        registration = TemplateRegistration('T', Path('/tmp/templates'), (), model, store)
        extension_manager.register_template(registration)
        assert extension_manager.templates['T'] is registration
        # 重复注册覆盖且不抛异常
        extension_manager.register_template(registration)
        assert extension_manager.templates['T'] is registration

    def test_unregister_template(self):
        model = build_template_config_model('T', {})
        store = ExtensionConfigStore(Path(CONFIG_ROOT), 'T', model)
        registration = TemplateRegistration('T', Path('/tmp/templates'), (), model, store)
        extension_manager.register_template(registration)
        extension_manager.unregister_template('T')
        assert extension_manager.templates == {}

    def test_register_resources(self):
        extension_manager.register_resources('R', Path('/tmp/resources'))
        assert extension_manager.resources['R'] == Path('/tmp/resources')
        extension_manager.unregister_resources('R')
        assert extension_manager.resources == {}


# ===== RendererManager =====


class TestRendererManager:
    def test_setup_activates_renderer(self):
        renderer = _FakeRenderer('fake')
        manager = RendererManager(lambda name: renderer if name == 'fake' else None)
        asyncio.run(manager.setup('fake'))
        assert renderer.setup_called
        assert manager._active['fake'] is renderer

    def test_setup_missing_engine_returns_none(self):
        # 配置的引擎不存在时不再回退，直接返回 None
        fallback = _FakeRenderer('html2pic')
        manager = RendererManager(lambda name: fallback if name == 'html2pic' else None)
        resolved = asyncio.run(manager.setup('nonexistent'))
        assert resolved is None
        assert not fallback.setup_called

    def test_setup_with_no_fallback_returns_none(self):
        manager = RendererManager(lambda name: None)
        assert asyncio.run(manager.setup('anything')) is None

    def test_setup_with_empty_name_returns_none(self):
        manager = RendererManager(lambda name: None)
        assert asyncio.run(manager.setup('')) is None

    def test_same_renderer_not_setup_twice(self):
        renderer = _FakeRenderer('fake')
        manager = RendererManager(lambda name: renderer)
        asyncio.run(manager.setup('fake'))
        asyncio.run(manager.setup('fake'))
        assert renderer.setup_called
        assert len([r for r in manager._active.values() if r is renderer]) == 1

    def test_render_delegates_to_active_engine(self):
        renderer = _FakeRenderer('fake')
        manager = RendererManager(lambda name: renderer if name == 'fake' else None)
        asyncio.run(manager.setup('fake'))
        result = asyncio.run(manager.render('<h1>x</h1>', 'body{}', name='fake'))
        assert result == b'fake:<h1>x</h1>:body{}'
        assert renderer.rendered == [('<h1>x</h1>', 'body{}')]

    def test_render_auto_setup_when_not_active(self):
        renderer = _FakeRenderer('fake')
        manager = RendererManager(lambda name: renderer if name == 'fake' else None)
        result = asyncio.run(manager.render('a', 'b', name='fake'))
        assert renderer.setup_called
        assert result == b'fake:a:b'

    def test_shutdown_cleans_all(self):
        renderer = _FakeRenderer('fake')
        manager = RendererManager(lambda name: renderer)
        asyncio.run(manager.setup('fake'))
        asyncio.run(manager.shutdown())
        assert renderer.shutdown_called
        assert manager._active == {}

    def test_render_without_engine_raises(self):
        manager = RendererManager(lambda name: None)
        with pytest.raises(RuntimeError):
            asyncio.run(manager.render('a', 'b'))


class _SizeAwareRenderer(BaseRenderer):
    """记录是否收到设计尺寸的假渲染器。"""

    name = 'size-aware'

    def __init__(self) -> None:
        self.received_size: tuple[int, int] | None = None

    async def setup(self) -> None:
        pass

    async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        self.received_size = size
        return b'size-aware'


class TestRenderSize:
    def test_size_threaded_to_renderer(self):
        renderer = _SizeAwareRenderer()
        manager = RendererManager(lambda name: renderer if name == 'size-aware' else None)
        asyncio.run(manager.setup('size-aware'))
        result = asyncio.run(manager.render('h', 'c', name='size-aware', size=(600, 800)))
        assert renderer.received_size == (600, 800)
        assert result == b'size-aware'


# ===== 资源包装（OnlineAsset / FileAsset）=====


class _FileUriRenderer(BaseRenderer):
    """模拟 playwright：本地文件需加 file:// 前缀。"""

    name = 'file-uri'

    async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        return b''

    def deal_file_asset(self, asset: FileAsset) -> str:
        return asset.path.as_uri()


class TestAssetWrapping:
    def test_default_deal_online_asset(self):
        renderer = _FakeRenderer('fake')
        assert renderer.deal_online_asset(OnlineAsset('https://example.com/a.png')) == 'https://example.com/a.png'

    def test_default_deal_file_asset(self):
        renderer = _FakeRenderer('fake')
        path = Path('/tmp/avatar.png')
        assert renderer.deal_file_asset(FileAsset(path)) == '/tmp/avatar.png'

    def test_override_deal_file_asset_adds_file_prefix(self):
        renderer = _FileUriRenderer()
        path = Path('/tmp/avatar.png')
        assert renderer.deal_file_asset(FileAsset(path)) == path.as_uri()

    def test_resolve_assets_with_renderer(self):
        manager = RendererManager(lambda name: None)
        renderer = _FileUriRenderer()
        context = {
            'avatar': FileAsset(Path('/tmp/a.png')),
            'icon': OnlineAsset('https://example.com/i.png'),
            'nested': {'bg': FileAsset(Path('/tmp/b.png'))},
            'items': [FileAsset(Path('/tmp/c.png'))],
            'plain': 'text',
        }
        resolved = manager._resolve_assets(context, renderer)
        assert resolved['avatar'] == Path('/tmp/a.png').as_uri()
        assert resolved['icon'] == 'https://example.com/i.png'
        assert resolved['nested']['bg'] == Path('/tmp/b.png').as_uri()
        assert resolved['items'] == [Path('/tmp/c.png').as_uri()]
        assert resolved['plain'] == 'text'

    def test_resolve_assets_with_none_renderer(self):
        manager = RendererManager(lambda name: None)
        context = {
            'avatar': FileAsset(Path('/tmp/a.png')),
            'icon': OnlineAsset('https://example.com/i.png'),
        }
        resolved = manager._resolve_assets(context, None)
        assert resolved['avatar'] == '/tmp/a.png'
        assert resolved['icon'] == 'https://example.com/i.png'

    def test_asset_str_without_renderer(self):
        # 未激活渲染器时，FileAsset 转字符串返回磁盘路径，OnlineAsset 返回 URL
        assert str(FileAsset(Path('/tmp/a.png'))) == '/tmp/a.png'
        assert str(OnlineAsset('https://example.com/i.png')) == 'https://example.com/i.png'

    def test_asset_str_with_active_renderer(self):
        # 激活渲染器后，FileAsset 转字符串按渲染器 deal_file_asset 处理
        import Scripts.Extensions.Renderer as renderer_module

        renderer = _FileUriRenderer()
        renderer_token = renderer_module._current_renderer.set(renderer)
        try:
            assert str(FileAsset(Path('/tmp/a.png'))) == Path('/tmp/a.png').as_uri()
            assert str(OnlineAsset('https://example.com/i.png')) == 'https://example.com/i.png'
        finally:
            renderer_module._current_renderer.reset(renderer_token)

    def test_resource_functions_return_wrappers(self):
        # 自带 Jinja2 资源函数返回 FileAsset 包装，由渲染器决定引用格式
        manager = RendererManager(lambda name: None)
        manager.register_resources('R', Path('/tmp/resources'))
        resource_file = Path('/tmp/resources/a.png')
        resource_file.parent.mkdir(parents=True, exist_ok=True)
        resource_file.write_bytes(b'png')
        try:
            path_asset = manager.resource_path('R', 'a.png')
            url_asset = manager.resource_url('R', 'a.png')
            assert isinstance(path_asset, FileAsset)
            assert isinstance(url_asset, FileAsset)
            assert path_asset.path == resource_file.resolve()
            assert url_asset.path == resource_file.resolve()
        finally:
            resource_file.unlink()
