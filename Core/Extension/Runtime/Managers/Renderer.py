"""
渲染引擎与模板/资源的运行时管理器。

`render_image()` 是唯一渲染入口：选择模板候选（`config.image.template` → `Default`）→
为模板协商渲染引擎（配置引擎优先，模板声明引擎兜底）→ 构建 Jinja2 环境 →
注入模板配置与资源函数 → 渲染 HTML/CSS → 委托渲染引擎输出 PNG 字节。
引擎注册、并发上限与单次超时也在此统一编排；扩展作者继承的定义在
`../Renderer.py`（BaseRenderer 与模板上下文相关定义）。
"""

from __future__ import annotations

import asyncio
import copy
from pathlib import Path
from random import choice
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, TemplateNotFound

from Core.Config import config
from Core.Logging import logger

from ...Errors import ExtensionError
from ...Renderer import (
    _IMAGE_SUFFIXES,
    _RESERVED_CONTEXT_KEYS,
    _RESOURCE_MAX_BYTES,
    FONT_PATH,
    BaseRenderer,
    FileAsset,
    OnlineAsset,
    TemplateRegistration,
    _current_renderer,
    _wrap_readonly,
    encode_context,
)
from ..Registries import RendererRegistry, ResourcesRegistry, TemplateRegistry

# 模板候选链末端的默认模板扩展 id（与注册表键一致）
DEFAULT_TEMPLATE_ID = 'Default'


def _renderer_failure_reason(registration: TemplateRegistration, configured_name: str) -> str:
    """描述某个模板候选无法使用配置渲染引擎的原因（供错误信息）。"""
    declared = [item.strip() for item in registration.support_renders if item.strip()]
    if not declared:
        return 'no support_renders declared'
    if configured_name:
        return f'render engine {configured_name!r} is not supported'
    return f'no available render engine among declared: {declared}'


class RendererManager:
    """统一管理渲染引擎与模板/资源注册，负责编排渲染与引擎并发/超时。"""

    def __init__(
        self,
        renderers: RendererRegistry | None = None,
        templates: TemplateRegistry | None = None,
        resources: ResourcesRegistry | None = None,
    ) -> None:
        # 注册容器由 ExtensionManager 创建后按引用传入；独立使用（测试）时自建
        self._renderers = renderers if renderers is not None else RendererRegistry()
        self._templates = templates if templates is not None else TemplateRegistry()
        self._resources = resources if resources is not None else ResourcesRegistry()
        # 已 setup 的引擎实例：name -> BaseRenderer
        self._active: dict[str, BaseRenderer] = {}
        # 各引擎并发上限与单次渲染超时（秒）
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._timeouts: dict[str, float] = {}
        self._default_timeout = 60.0
        # Jinja2 环境缓存：extension_id -> Environment | None（None 表示待重建）
        self._environments: dict[str, Environment | None] = {}

    # ---------- 注册接口 ----------

    def register(self, renderer: BaseRenderer, *, owner_id: str = '') -> None:
        """注册一个渲染引擎实例（无名称的渲染器忽略）。"""
        self._renderers.register(renderer, owner_id=owner_id)

    @property
    def renderers(self) -> dict[str, BaseRenderer]:
        """已注册的渲染引擎表：name -> BaseRenderer。"""
        return self._renderers.all()

    @property
    def templates(self) -> dict[str, TemplateRegistration]:
        """已注册的 template 扩展包：id -> TemplateRegistration。"""
        return self._templates.all()

    @property
    def resources(self) -> dict[str, Path]:
        """已注册的 resources 扩展包：id -> 资源根目录。"""
        return self._resources.all()

    def reset(self) -> None:
        """清空渲染引擎与模板/资源注册（重新加载前调用）。"""
        self._renderers.clear()
        self._templates.clear()
        self._resources.clear()
        self._environments.clear()
        # 已 setup 的引擎实例与并发/超时配置一并清理，避免下次 setup 复用陈旧引擎
        self._active.clear()
        self._semaphores.clear()
        self._timeouts.clear()

    def get_renderer(self, name: str) -> BaseRenderer | None:
        """按名称获取已注册的渲染引擎实例。"""
        return self._renderers.get(name)

    def unregister_renderers_by_owner(self, owner_id: str) -> list[str]:
        """注销某扩展登记的全部渲染引擎（供声明回滚使用）。"""
        return self._renderers.unregister_by_owner(owner_id)

    def register_template(self, registration: TemplateRegistration) -> None:
        """注册 template 无代码扩展；重复注册覆盖并失效缓存。"""
        self._templates.register(registration)
        self._environments.pop(registration.extension_id, None)
        logger.info(f'Template extension {registration.extension_id} registered.')

    def unregister_template(self, extension_id: str) -> None:
        """注销 template 扩展并清理缓存。"""
        self._templates.unregister(extension_id)
        self._environments.pop(extension_id, None)

    def register_resources(self, extension_id: str, resources_dir: Path) -> None:
        """注册 resources 无代码扩展。"""
        self._resources.register(extension_id, resources_dir)
        logger.info(f'Resource extension {extension_id} registered.')

    def unregister_resources(self, extension_id: str) -> None:
        """注销 resources 扩展。"""
        self._resources.unregister(extension_id)

    # ---------- 模板环境与配置 ----------

    def invalidate_template(self, extension_id: str) -> None:
        """使指定模板扩展的 Jinja2 环境失效（配置更新后调用）。"""
        if extension_id in self._environments:
            self._environments[extension_id] = None

    def invalidate_all(self) -> None:
        """使全部模板扩展的 Jinja2 环境失效（模板热切换）。"""
        for template_id in self._environments:
            self._environments[template_id] = None

    def _build_environment(self, template_id: str) -> Environment:
        """构建 Jinja2 环境：当前模板优先，默认模板（default）回退。"""
        loaders = []
        registration = self._templates.get(template_id)
        if registration is not None:
            loaders.append(FileSystemLoader(str(registration.templates_dir)))
        # 默认模板扩展作为最终回退
        default_reg = self._templates.get(DEFAULT_TEMPLATE_ID)
        if default_reg is not None and default_reg.extension_id != template_id:
            loaders.append(FileSystemLoader(str(default_reg.templates_dir)))
        if not loaders:
            raise RuntimeError(
                f'Template extension {template_id} does not exist and no default template is available, please make sure the default template extension is enabled!'
            )
        environment = Environment(loader=ChoiceLoader(loaders), enable_async=True)
        environment.globals['random'] = self.random_image
        environment.globals['resource_path'] = self.resource_path
        environment.globals['resource_url'] = self.resource_url
        environment.globals['resource_text'] = self.resource_text
        environment.globals['resource_bytes'] = self.resource_bytes
        return environment

    def _get_environment(self, template_id: str) -> Environment:
        """获取指定模板扩展的环境，惰性构建并缓存。"""
        if template_id not in self._environments:
            self._environments[template_id] = self._build_environment(template_id)
        environment = self._environments[template_id]
        assert environment is not None
        return environment

    def _template_candidates(self) -> list[TemplateRegistration]:
        """
        生成模板候选链：`config.image.template` → `Default`（去重、忽略未注册项）。

            配置模板缺失时回退默认模板；链为空表示没有任何可用模板。
        """
        configured = (config.image.template or '').strip()
        candidates: list[TemplateRegistration] = []
        for template_id in (configured, DEFAULT_TEMPLATE_ID):
            if not template_id:
                continue
            registration = self._templates.get(template_id)
            if registration is None:
                if template_id == configured and configured != DEFAULT_TEMPLATE_ID:
                    logger.warning(
                        f'Template extension {template_id} not found, falling back to template {DEFAULT_TEMPLATE_ID}.'
                    )
                continue
            if all(item.extension_id != registration.extension_id for item in candidates):
                candidates.append(registration)
        return candidates

    async def _config_context(self, registration: TemplateRegistration) -> Any:
        """
        模板配置快照：预渲染含 {{ }} 的字符串字段后深拷贝并包装为只读对象。

            配置值可引用其他配置字段或资源函数（如
            background = 'url("{{ resource_url("Resources", "a.png") }}")'）。
        """
        data = registration.config_store.value.model_dump(mode='json')
        environment = self._get_environment(registration.extension_id)
        for field_name, value in data.items():
            if isinstance(value, str) and '{{' in value:
                data[field_name] = await environment.from_string(value).render_async(**data)
        return _wrap_readonly(copy.deepcopy(data))

    async def _load_style(self, environment: Environment, path: str, **context):
        """加载 base.css + 模板专属 css，并通过 Jinja2 异步渲染。"""

        parts = []
        name = path.split('/')[-1]
        for css_name in ('Base.css', f'{path}/{name}.css'):
            try:
                template = environment.get_template(css_name)
                parts.append(await template.render_async(**context))
            except TemplateNotFound:
                continue
        return '\n'.join(parts)

    # ---------- 资源访问（模板可调用的资源函数） ----------

    def _resolve_font_path(self) -> Path:
        """
        解析默认字体路径。

            优先使用 `config.image.font` 显式指定的字体文件；未配置时从已注册
            资源扩展根目录中查找 Font.ttf（如 Default 扩展的 Resources/），
            其次回退旧版内置路径（UniBot/Resources/Font.ttf，兼容历史安装）；
            均未找到时抛出明确错误。
        """
        configured = (config.image.font or '').strip()
        if configured:
            path = Path(configured).expanduser().resolve()
            if not path.is_file():
                raise ExtensionError(f'Configured font file does not exist: {configured}')
            return path
        for root in self._resources.all().values():
            candidate = (root / 'Font.ttf').resolve()
            if candidate.is_file():
                return candidate
        if FONT_PATH.is_file():
            return FONT_PATH
        raise ExtensionError(
            'Default font Font.ttf not found, please make sure the default resource extension is loaded!'
        )

    def _resolve_resource(self, extension_id: str, relative_path: str) -> Path:
        """解析资源文件，校验资源已注册、路径不越界且文件存在。"""
        root = self._resources.get(extension_id)
        if root is None:
            raise ExtensionError(f'Resource extension {extension_id} is not registered!')
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ExtensionError(f'Resource path out of bounds: {extension_id}/{relative_path}')
        if not path.is_file():
            raise ExtensionError(f'Resource file does not exist: {extension_id}/{relative_path}')
        return path

    def random_image(self, extension_id: str, directory: str) -> str:
        """
        从指定资源扩展的目录中随机挑选一张图片，返回可直接用于 CSS
        background-image 的 url("...") 字符串。

            作为 Jinja 全局函数 `random` 使用，模板或配置中均可调用：
            background = '{{ random("Default", "Backgrounds") }}'。
            directory 相对资源扩展根目录解析，不允许越界。
            路径经 `FileAsset` 包装，由当前渲染器决定引用格式。
        """
        root = self._resources.get(extension_id)
        if root is None:
            raise ExtensionError(f'Resource extension {extension_id} is not registered!')
        path = (root / directory).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ExtensionError(f'Resource path out of bounds: {extension_id}/{directory}')
        if not path.is_dir():
            logger.warning(f'RandomImage error: directory not found: {extension_id}/{directory}')
            return ''
        images = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES]
        if not images:
            logger.warning(f'RandomImage error: no images found in directory: {extension_id}/{directory}')
            return ''
        return f'url("{FileAsset(choice(images))}")'

    def resource_path(self, extension_id: str, relative_path: str) -> FileAsset:
        """返回资源文件的本地文件包装（由渲染器决定引用格式，如 playwright 需 file://）。"""
        return FileAsset(self._resolve_resource(extension_id, relative_path))

    # 与 resource_path 同实现：为模板语义保留两个名称（url 强调用于引用，path 强调本地路径）
    resource_url = resource_path

    def resource_text(self, extension_id: str, relative_path: str, encoding: str = 'Utf-8') -> str:
        """以文本形式读取资源内容（单次读取上限 2 MiB）。"""
        path = self._resolve_resource(extension_id, relative_path)
        data = path.read_bytes()
        if len(data) > _RESOURCE_MAX_BYTES:
            raise ExtensionError(
                f'Resource file too large: {extension_id}/{relative_path} ({len(data)} bytes > {_RESOURCE_MAX_BYTES})!'
            )
        return data.decode(encoding)

    def resource_bytes(self, extension_id: str, relative_path: str) -> bytes:
        """以字节形式读取资源内容（单次读取上限 2 MiB）。"""
        path = self._resolve_resource(extension_id, relative_path)
        data = path.read_bytes()
        if len(data) > _RESOURCE_MAX_BYTES:
            raise ExtensionError(
                f'Resource file too large: {extension_id}/{relative_path} ({len(data)} bytes > {_RESOURCE_MAX_BYTES})!'
            )
        return data

    # ---------- 渲染编排入口 ----------

    def _resolve_assets(self, value: Any, renderer: BaseRenderer | None) -> Any:
        """
        递归把上下文中的资源包装（OnlineAsset/FileAsset）转换为渲染器可用字符串。

            渲染器为 None 时按默认规则转换（在线 URL 原样、本地文件返回磁盘路径），
            保证后续 JSON 编码不因包装对象而失败。
        """
        if isinstance(value, OnlineAsset):
            return value.url if renderer is None else renderer.deal_online_asset(value)
        if isinstance(value, FileAsset):
            return str(value.path) if renderer is None else renderer.deal_file_asset(value)
        if isinstance(value, dict):
            return {key: self._resolve_assets(item, renderer) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_assets(item, renderer) for item in value]
        return value

    async def _resolve_renderer(self, registration: TemplateRegistration, configured_name: str) -> BaseRenderer | None:
        """
        为指定模板协商渲染引擎：配置引擎优先，其次模板声明的引擎。

            `support_renders` 声明模板支持的引擎：`['*']` = 全部支持，否则为具体 name 列表。
            配置引擎受支持且可用时优先；其次按声明顺序取第一个可用引擎；`['*']` 时
            未配置/不可用则回退首个已注册引擎。均不可用返回 None。
            引擎名比较大小写不敏感。
        """
        declared = [item.strip().lower() for item in registration.support_renders if item.strip()]
        unrestricted = '*' in declared
        named = [item for item in declared if item != '*']
        configured = configured_name.strip()
        tried: set[str] = set()
        if configured and (unrestricted or configured.lower() in named):
            tried.add(configured.lower())
            renderer = await self._try_setup(configured)
            if renderer is not None:
                return renderer
        for candidate in named:
            if candidate in tried:
                continue
            tried.add(candidate)
            renderer = await self._try_setup(candidate)
            if renderer is not None:
                self._log_renderer_choice(registration, renderer, configured_name)
                return renderer
        if unrestricted:
            # 模板声明支持全部引擎：回退到首个已注册引擎
            for name in self._renderers.all():
                if name.lower() in tried:
                    continue
                tried.add(name.lower())
                renderer = await self._try_setup(name)
                if renderer is not None:
                    self._log_renderer_choice(registration, renderer, configured_name)
                    return renderer
        return None

    @staticmethod
    def _log_renderer_choice(registration: TemplateRegistration, renderer: BaseRenderer, configured_name: str) -> None:
        """记录非配置引擎的选择（自动降级时给出原因）。"""
        if configured_name:
            logger.warning(
                f'Render engine {configured_name!r} is unavailable for template {registration.extension_id}, '
                f'switching to render engine {renderer.name!r}.'
            )
        else:
            logger.warning(
                f'No render engine configured, using render engine {renderer.name!r} '
                f'for template {registration.extension_id}.'
            )

    async def _try_setup(self, name: str) -> BaseRenderer | None:
        """尝试初始化引擎；失败时视为不可用并记录日志，供协商继续尝试下一候选。"""
        try:
            return await self.setup(name)
        except Exception as error:
            logger.warning(f'Render engine {name} failed to set up: {error}')
            return None

    @staticmethod
    def _unsupported_renderer_error(configured_name: str, attempts: list[tuple[str, str]]) -> str:
        """构造模板无法使用指定渲染引擎时的错误信息（含每个候选的失败原因）。"""
        reasons = '; '.join(f'{template_id}: {reason}' for template_id, reason in attempts)
        detail = f' details -> {reasons}' if reasons else ''
        if configured_name:
            prefix = f'current template does not support render engine {configured_name!r}'
        else:
            prefix = 'no available render engine for current template'
        return (
            f'{prefix}{detail}, please select a supported render engine '
            'or install a compatible render engine extension!'
        )

    async def render_image(
        self,
        template: str,
        size: tuple[int, int],
        *,
        context: dict | None = None,
        renderer: str | None = None,
    ) -> bytes:
        """
        渲染模板为 PNG 图片字节（唯一编排入口）。

            template: 模板包内模板名称，如 'List'，对应模板目录下的 List/List.html。
            size: (width, height)。
            context: 模板变量；`config`/资源函数等保留名称由框架注入，冲突立即报错。
                上下文中的图片/字体资源可用 `OnlineAsset`/`FileAsset` 包装，
                由渲染器的 `deal_online_asset`/`deal_file_asset` 转换为可用字符串。
            renderer: 渲染引擎名称，缺省用 `config.image.renderer`。

            模板候选链：`config.image.template` → `Default`；每个候选先看配置引擎是否
            受模板 `support_renders` 支持，不支持时改用模板声明的引擎；
            候选模板全部不可用时抛出错误。
        """
        candidates = self._template_candidates()
        if not candidates:
            installed = ', '.join(self._templates.all()) or 'none'
            raise RuntimeError(
                'No usable template extension found, please make sure the default template extension is enabled! '
                f'Installed templates: {installed}.'
            )
        configured_name = renderer or config.image.renderer
        configured_template = (config.image.template or '').strip()
        attempts: list[tuple[str, str]] = []
        for registration in candidates:
            active_renderer = await self._resolve_renderer(registration, configured_name)
            if active_renderer is None:
                attempts.append((registration.extension_id, _renderer_failure_reason(registration, configured_name)))
                continue
            if registration.extension_id != configured_template:
                logger.warning(
                    f'Template {configured_template} is unavailable, rendering with template '
                    f'{registration.extension_id} and render engine {active_renderer.name}.'
                )
            return await self._render_with_template(
                template,
                size,
                registration,
                active_renderer,
                context,
            )
        raise ExtensionError(self._unsupported_renderer_error(configured_name, attempts))

    async def _render_with_template(
        self,
        template: str,
        size: tuple[int, int],
        registration: TemplateRegistration,
        active_renderer: BaseRenderer,
        context: dict | None,
    ) -> bytes:
        """构建模板环境并编排一次完整渲染（含资源依赖检查与激活渲染器上下文）。"""
        environment = self._get_environment(registration.extension_id)
        # 资源依赖检查
        missing = [rid for rid in registration.resource_ids if rid not in self._resources]
        if missing:
            raise ExtensionError(
                f'template {registration.extension_id} declares unregistered resource extensions: {missing}'
            )
        # 设置当前渲染器，供 Jinja2 资源函数把包装转换为渲染器可用字符串
        renderer_token = _current_renderer.set(active_renderer)
        try:
            return await self._render_with_renderer(
                template,
                size,
                registration,
                environment,
                active_renderer,
                context,
            )
        finally:
            _current_renderer.reset(renderer_token)

    async def _render_with_renderer(
        self,
        template: str,
        size: tuple[int, int],
        registration: TemplateRegistration,
        environment: Environment,
        active_renderer: BaseRenderer,
        context: dict | None,
    ) -> bytes:
        """在已激活渲染器的上下文中完成上下文构建与 HTML/CSS 渲染。"""
        width, height = size
        # 上下文构建：先解析扩展传入的资源包装，再做 JSON 编码 + HTML 转义
        raw_user_context = dict(context or {})
        user_context = encode_context(self._resolve_assets(raw_user_context, active_renderer))
        conflicts = _RESERVED_CONTEXT_KEYS & set(user_context)
        if conflicts:
            raise ExtensionError(
                f'template {registration.extension_id} uses reserved context names: {sorted(conflicts)}'
            )
        # 字体链接同样经渲染器处理（如 playwright 需 file:// 前缀）
        font_path = self._resolve_font_path()
        font_uri = active_renderer.deal_file_asset(FileAsset(font_path))
        injected = {
            'config': await self._config_context(registration),
            'width': width,
            'height': height,
            'font_uri': font_uri,
        }
        merged = {**injected, **user_context}
        template_name = template.split('/')[-1]
        # 渲染 HTML 与 CSS
        try:
            html_template = environment.get_template(f'{template}/{template_name}.html')
        except TemplateNotFound as error:
            raise ExtensionError(
                f'template {registration.extension_id} does not contain template: {template}'
            ) from error
        css_task = self._load_style(environment, template, **merged)
        html_content, css_content = await asyncio.gather(
            html_template.render_async(**merged),
            css_task,
        )
        return await self.render(
            html_content,
            css_content,
            active_renderer.name,
            (width, height),
        )

    # ---------- 引擎管理 ----------

    def configure(self, name: str, concurrency: int = 1, timeout: float | None = None) -> None:
        """配置指定引擎的并发上限与单次渲染超时。"""
        self._semaphores[name] = asyncio.Semaphore(max(1, concurrency))
        if timeout is not None:
            self._timeouts[name] = timeout

    async def setup(self, name: str) -> BaseRenderer | None:
        """初始化并启用指定引擎（名称大小写不敏感），未选择或不存在时返回 None。"""
        if not name:
            logger.error('No render engine selected!')
            return None
        resolved = self._renderers.resolve_name(name)
        if resolved is None:
            logger.error(f'Render engine {name} does not exist!')
            return None
        renderer = self._renderers.get(resolved)
        assert renderer is not None
        if resolved in self._active:
            return renderer
        await renderer.setup()
        self._active[resolved] = renderer
        if resolved not in self._semaphores:
            # 默认并发 = 1：渲染引擎（浏览器内核等）通常不支持并发页面安全复用
            self._semaphores[resolved] = asyncio.Semaphore(1)
        logger.info(f'Render engine {renderer.name} is ready.')
        return renderer

    async def render(
        self, html_content: str, css: str, name: str | None = None, size: tuple[int, int] | None = None
    ) -> bytes:
        """使用指定引擎渲染 HTML+CSS 为 PNG 字节，带并发上限与超时。

        size: (宽度, 高度)，透传给渲染器的 render，供布局视口使用。
        """
        if not name:
            raise RuntimeError('No render engine selected!')
        renderer = self._active.get(name)
        if renderer is None:
            renderer = await self.setup(name)
        if renderer is None:
            raise RuntimeError(f'Render engine {name} is unavailable!')
        semaphore = self._semaphores.get(renderer.name)
        timeout = self._timeouts.get(renderer.name, self._default_timeout)
        if semaphore is None:
            raise RuntimeError(f'Semaphore for render engine {renderer.name} is not configured!')
        async with semaphore:
            return await asyncio.wait_for(renderer.render(html_content, css, size), timeout=timeout)

    async def shutdown(self) -> None:
        """清理全部已启用引擎。"""
        for renderer in self._active.values():
            try:
                await renderer.shutdown()
            except Exception as error:
                logger.error(f'Render engine {renderer.name} failed to shut down: {error}')
        self._active.clear()
        self._renderers.clear()