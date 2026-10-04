"""渲染扩展测试（A4）：渲染器注册、RendererManager 激活/回退/清理、模板/资源注册。"""

import asyncio
from pathlib import Path

import pytest

from Core.Config import config
from Core.Extension import BaseRenderer, ExtensionError, RendererManager, extension_manager
from Core.Extension.Renderer import (
    FileAsset,
    OnlineAsset,
    TemplateRegistration,
)
from Core.Extension.Runtime.Loader import CONFIG_ROOT
from Core.Extension.Storage import ExtensionConfigStore
from Core.Extension.TemplateConfig import build_template_config_model


class _FakeImageConfig:
    """渲染测试用的 [image] 配置替身。"""

    template = 'Default'
    font = ''
    renderer = ''


@pytest.fixture(autouse=True)
def _stub_image_config(monkeypatch):
    """用配置替身替换全局 [image]，使渲染测试不依赖真实 Config.toml。"""
    monkeypatch.setattr(config, 'image', _FakeImageConfig())


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


def _make_manager(*renderers: BaseRenderer) -> RendererManager:
    """构造已注册指定渲染引擎的 RendererManager。"""
    manager = RendererManager()
    for renderer in renderers:
        manager.register(renderer)
    return manager


def _make_template(
    template_id: str,
    support_renders: tuple[str, ...] = (),
    templates_dir: Path = Path('/tmp/templates'),
) -> TemplateRegistration:
    """构造测试用模板注册（空配置模型 + 独立配置存储）。"""
    model = build_template_config_model(template_id, {})
    store = ExtensionConfigStore(Path(CONFIG_ROOT), template_id, model)
    return TemplateRegistration(template_id, templates_dir, (), model, store, support_renders)


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
        manager = _make_manager(renderer)
        asyncio.run(manager.setup('fake'))
        assert renderer.setup_called
        assert manager._active['fake'] is renderer

    def test_setup_missing_engine_returns_none(self):
        # 配置的引擎不存在时不再回退，直接返回 None
        fallback = _FakeRenderer('html2pic')
        manager = _make_manager(fallback)
        resolved = asyncio.run(manager.setup('nonexistent'))
        assert resolved is None
        assert not fallback.setup_called

    def test_setup_with_no_fallback_returns_none(self):
        manager = RendererManager()
        assert asyncio.run(manager.setup('anything')) is None

    def test_setup_with_empty_name_returns_none(self):
        manager = RendererManager()
        assert asyncio.run(manager.setup('')) is None

    def test_same_renderer_not_setup_twice(self):
        renderer = _FakeRenderer('fake')
        manager = _make_manager(renderer)
        asyncio.run(manager.setup('fake'))
        asyncio.run(manager.setup('fake'))
        assert renderer.setup_called
        assert len([r for r in manager._active.values() if r is renderer]) == 1

    def test_render_delegates_to_active_engine(self):
        renderer = _FakeRenderer('fake')
        manager = _make_manager(renderer)
        asyncio.run(manager.setup('fake'))
        result = asyncio.run(manager.render('<h1>x</h1>', 'body{}', name='fake'))
        assert result == b'fake:<h1>x</h1>:body{}'
        assert renderer.rendered == [('<h1>x</h1>', 'body{}')]

    def test_render_auto_setup_when_not_active(self):
        renderer = _FakeRenderer('fake')
        manager = _make_manager(renderer)
        result = asyncio.run(manager.render('a', 'b', name='fake'))
        assert renderer.setup_called
        assert result == b'fake:a:b'

    def test_shutdown_cleans_all(self):
        renderer = _FakeRenderer('fake')
        manager = _make_manager(renderer)
        asyncio.run(manager.setup('fake'))
        asyncio.run(manager.shutdown())
        assert renderer.shutdown_called
        assert manager._active == {}

    def test_render_without_engine_raises(self):
        manager = RendererManager()
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
        manager = _make_manager(renderer)
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
        manager = RendererManager()
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
        manager = RendererManager()
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
        import Core.Extension.Renderer as renderer_module

        renderer = _FileUriRenderer()
        renderer_token = renderer_module._current_renderer.set(renderer)
        try:
            assert str(FileAsset(Path('/tmp/a.png'))) == Path('/tmp/a.png').as_uri()
            assert str(OnlineAsset('https://example.com/i.png')) == 'https://example.com/i.png'
        finally:
            renderer_module._current_renderer.reset(renderer_token)

    def test_resource_functions_return_wrappers(self):
        # 自带 Jinja2 资源函数返回 FileAsset 包装，由渲染器决定引用格式
        manager = RendererManager()
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


# ===== 渲染引擎协商（模板声明 support_renders） =====


class TestRendererNegotiation:
    def test_configured_renderer_used_when_declared(self):
        renderer = _FakeRenderer('html2pic')
        manager = _make_manager(renderer)
        registration = _make_template('T', support_renders=('html2pic', 'playwright'))
        assert asyncio.run(manager._resolve_renderer(registration, 'html2pic')) is renderer

    def test_declared_renderer_used_when_configured_unsupported(self):
        # 配置引擎不在模板声明中，模板声明的引擎已注册 → 自动切换
        html2pic = _FakeRenderer('html2pic')
        playwright = _FakeRenderer('playwright')
        manager = _make_manager(html2pic, playwright)
        registration = _make_template('T', support_renders=('playwright',))
        assert asyncio.run(manager._resolve_renderer(registration, 'html2pic')) is playwright

    def test_falls_back_to_next_declared_when_first_unavailable(self):
        playwright = _FakeRenderer('playwright')
        manager = _make_manager(playwright)
        registration = _make_template('T', support_renders=('html2pic', 'playwright'))
        # html2pic 未注册，声明链中的 playwright 可用
        assert asyncio.run(manager._resolve_renderer(registration, 'html2pic')) is playwright

    def test_returns_none_when_no_declared_renderer_available(self):
        manager = _make_manager(_FakeRenderer('playwright'))
        registration = _make_template('T', support_renders=('html2pic',))
        assert asyncio.run(manager._resolve_renderer(registration, 'playwright')) is None

    def test_wildcard_allows_any_engine(self):
        # support_renders = ['*']：任意已注册引擎均可，配置引擎优先
        html2pic = _FakeRenderer('html2pic')
        playwright = _FakeRenderer('playwright')
        manager = _make_manager(html2pic, playwright)
        registration = _make_template('T', support_renders=('*',))
        assert asyncio.run(manager._resolve_renderer(registration, 'playwright')) is playwright

    def test_wildcard_falls_back_to_registered_engine(self):
        # support_renders = ['*'] 且未配置引擎：回退到首个已注册引擎
        renderer = _FakeRenderer('playwright')
        manager = _make_manager(renderer)
        registration = _make_template('T', support_renders=('*',))
        assert asyncio.run(manager._resolve_renderer(registration, '')) is renderer

    def test_empty_support_renders_matches_nothing(self):
        # 空声明不匹配任何引擎（清单校验会阻止其注册，运行时亦兜底拒绝）
        manager = _make_manager(_FakeRenderer('playwright'))
        registration = _make_template('T', support_renders=())
        assert asyncio.run(manager._resolve_renderer(registration, 'playwright')) is None

    def test_renderer_name_case_insensitive(self):
        renderer = _FakeRenderer('Html2Pic')
        manager = _make_manager(renderer)
        registration = _make_template('T', support_renders=('html2pic',))
        assert asyncio.run(manager._resolve_renderer(registration, 'html2pic')) is renderer

    def test_setup_failure_skips_to_next_declared(self):
        class _BrokenRenderer(BaseRenderer):
            name = 'html2pic'

            async def setup(self) -> None:
                raise RuntimeError('engine broken')

            async def render(self, html: str, css: str, size: tuple[int, int] | None = None) -> bytes:
                return b''

        playwright = _FakeRenderer('playwright')
        manager = _make_manager(_BrokenRenderer(), playwright)
        registration = _make_template('T', support_renders=('html2pic', 'playwright'))
        # html2pic setup 失败 → 视为不可用，切到 playwright
        assert asyncio.run(manager._resolve_renderer(registration, 'html2pic')) is playwright

    def test_template_candidates_prefer_configured(self, monkeypatch):
        manager = RendererManager()
        manager.register_template(_make_template('Default'))
        manager.register_template(_make_template('Custom'))
        monkeypatch.setattr(config.image, 'template', 'Custom')
        candidate_ids = [item.extension_id for item in manager._template_candidates()]
        # 配置模板优先，Default 作为末端回退
        assert candidate_ids == ['Custom', 'Default']

    def test_template_candidates_deduplicate_default(self, monkeypatch):
        manager = RendererManager()
        manager.register_template(_make_template('Default'))
        monkeypatch.setattr(config.image, 'template', 'Default')
        candidates = manager._template_candidates()
        assert [item.extension_id for item in candidates] == ['Default']

    def test_render_image_errors_when_no_renderer_supports_template(self, monkeypatch):
        manager = _make_manager(_FakeRenderer('playwright'))
        manager.register_template(_make_template('Default', support_renders=('html2pic',)))
        monkeypatch.setattr(config.image, 'template', 'Default')
        monkeypatch.setattr(config.image, 'renderer', 'playwright')
        with pytest.raises(ExtensionError):
            asyncio.run(manager.render_image('List', (600, 800)))

    def test_render_image_switches_to_declared_renderer(self, tmp_path, monkeypatch):
        # 配置引擎未安装，模板声明支持已安装的 html2pic → 自动切换并渲染成功
        manager = _make_manager(_FakeRenderer('html2pic'))
        manager.register_template(_make_default_template(tmp_path, ('html2pic',)))
        manager.register_resources('DefaultResources', tmp_path)
        monkeypatch.setattr(config.image, 'template', 'Default')
        monkeypatch.setattr(config.image, 'renderer', 'playwright')
        result = asyncio.run(manager.render_image('List', (600, 800)))
        assert result.startswith(b'html2pic:')

    def test_render_image_falls_back_to_default_template(self, tmp_path, monkeypatch):
        # 配置模板缺失 → 回退 Default 并成功渲染
        manager = _make_manager(_FakeRenderer('html2pic'))
        manager.register_template(_make_default_template(tmp_path, ('*',)))
        manager.register_resources('DefaultResources', tmp_path)
        monkeypatch.setattr(config.image, 'template', 'MissingTemplate')
        monkeypatch.setattr(config.image, 'renderer', 'html2pic')
        result = asyncio.run(manager.render_image('List', (600, 800)))
        assert result.startswith(b'html2pic:')


def _make_default_template(tmp_path: Path, support_renders: tuple[str, ...] = ('*',)) -> TemplateRegistration:
    """构造带真实模板目录与字体的 Default 模板注册（供端到端渲染测试）。"""
    templates_dir = tmp_path / 'Templates'
    (templates_dir / 'List').mkdir(parents=True)
    (templates_dir / 'List' / 'List.html').write_text('<h1>{{ width }}</h1>', 'Utf-8')
    (tmp_path / 'Font.ttf').write_bytes(b'font')
    return _make_template('Default', support_renders, templates_dir)
