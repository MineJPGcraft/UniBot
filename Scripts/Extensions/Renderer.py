"""
渲染引擎基类、模板/资源注册表与统一渲染编排入口。

分层模型（见 Plan.md）：
- `renderer` 扩展：提供 HTML+CSS -> PNG 的渲染引擎（如 html2pic）。
- `template` 扩展：无代码扩展包，含 Jinja2 模板目录与受限配置 schema
  （`[template].config_schema`），配置经 `ExtensionConfigStore` 独立存储，
  在模板中以 `config.xxx` 访问。
- `resources` 扩展：无代码扩展包，提供模板可引用的静态资源根目录。

`RendererManager.render_image()` 是唯一渲染入口：选择模板包 -> 构建
Jinja2 环境（当前模板优先、默认模板回退）-> 注入模板配置与资源函数 ->
渲染 HTML/CSS -> 委托渲染引擎输出 PNG 字节。
"""

from __future__ import annotations

import asyncio
import copy
import html
import json
import re
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from random import choice
from typing import TYPE_CHECKING, Any, Literal

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, ConfigDict, Field, create_model

from Scripts.Logging import logger

from ..Config import config
from .Base import TemplateFieldConfig
from .Errors import ExtensionError
from .Storage import ExtensionConfigStore

if TYPE_CHECKING:
    from .Manager import ExtensionManager

# 模板根目录（UniBot/Resources），默认字体所在处
RESOURCES_DIR = Path(__file__).parent.parent.parent / 'Resources'
FONT_PATH: Path = RESOURCES_DIR / 'Font.ttf'

# 支持的图片扩展名
_IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
# 受限配置字段名：合法 Python 标识符且不以 _ 开头
_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# 颜色：#RRGGBB 或 #RRGGBBAA
_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$')
# 单次资源读取上限（2 MiB）
_RESOURCE_MAX_BYTES = 2 * 1024 * 1024

# 保留名称：模板上下文保留名称，调用方不得覆盖
_RESERVED_CONTEXT_KEYS = {
    'config',
    'width',
    'height',
    'font_uri',
    'random',
    'resource_path',
    'resource_url',
    'resource_text',
    'resource_bytes',
}


def encode_context(context: dict) -> dict:
    """对模板上下文做 JSON 编码 + HTML 转义，防止注入。"""
    return json.loads(html.escape(json.dumps(context), False))


def build_template_config_model(
    extension_id: str,
    schema: dict[str, TemplateFieldConfig],
) -> type[BaseModel]:
    """
    把清单受限 config_schema 编译为 Pydantic 模型。

        字段名必须为合法 Python 标识符且不以 `_` 开头；每项必须提供类型与
        默认值。类型仅限 `string/integer/number/boolean/color/select`，约束
        与类型不匹配、select 缺选项或默认值不在选项中等情况一律阻止注册。
    """
    fields: dict[str, tuple[Any, Any]] = {}
    for field_name, field_cfg in schema.items():
        if not _IDENTIFIER_RE.match(field_name) or field_name.startswith('_'):
            raise ExtensionError(
                f'template {extension_id} 配置字段名非法：{field_name}！字段名必须是合法 Python 标识符且不能以下划线开头！'
            )
        fields[field_name] = _map_template_field(extension_id, field_name, field_cfg)
    return create_model(
        f'TemplateConfig_{extension_id}',
        __config__=ConfigDict(extra='forbid'),
        **fields,  # type: ignore[arg-type]
    )


def _reject_misplaced_constraints(
    cfg: TemplateFieldConfig,
    reject: Callable[[str], ExtensionError],
    *,
    allow_min_max: bool = False,
    allow_length: bool = False,
    allow_options: bool = False,
) -> None:
    """校验约束字段与当前类型匹配，错位约束（如数值字段的 options）一律拒绝。"""
    if not allow_min_max and (cfg.min is not None or cfg.max is not None):
        raise reject('min/max only apply to integer/number')
    if not allow_length and (cfg.min_length is not None or cfg.max_length is not None):
        raise reject('min_length/max_length only apply to string')
    if not allow_options and cfg.options:
        raise reject('options only apply to select')


def _map_template_field(
    extension_id: str,
    field_name: str,
    cfg: TemplateFieldConfig,
) -> tuple[Any, Any]:
    """按类型映射为 Pydantic 字段，并校验约束与默认值合法性。"""
    field_type = cfg.type
    default = cfg.default

    def reject(reason: str) -> ExtensionError:
        return ExtensionError(f'template {extension_id} config field {field_name} {reason}')

    # 保留 title/description 与原始类型标记（color/select 编译后类型会丢失）
    field_kwargs: dict[str, Any] = {'json_schema_extra': {'template_type': field_type}}
    if cfg.title:
        field_kwargs['title'] = cfg.title
    if cfg.description:
        field_kwargs['description'] = cfg.description

    def typed_number_constraint(target: type) -> dict[str, Any]:
        """构造数值范围约束，min/max 类型不符时拒绝。"""
        constraints: dict[str, Any] = {}
        if cfg.min is not None:
            if not isinstance(cfg.min, target) or isinstance(cfg.min, bool):
                raise reject(f'min must be of type {target.__name__}')
            constraints['ge'] = cfg.min
        if cfg.max is not None:
            if not isinstance(cfg.max, target) or isinstance(cfg.max, bool):
                raise reject(f'max must be of type {target.__name__}')
            constraints['le'] = cfg.max
        return constraints

    def length_constraints() -> dict[str, Any]:
        """构造字符串长度约束，取值非法时拒绝。"""
        constraints: dict[str, Any] = {}
        for attr, key in (('min_length', 'min_length'), ('max_length', 'max_length')):
            value = getattr(cfg, attr)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise reject(f'{attr} must be a non-negative integer')
            constraints[key] = value
        return constraints

    if field_type in ('integer', 'number'):
        target = int if field_type == 'integer' else float
        if not isinstance(default, target) or isinstance(default, bool):
            raise reject(f'default must be of type {target.__name__}')
        _reject_misplaced_constraints(cfg, reject, allow_min_max=True)
        return (target, Field(default=default, **typed_number_constraint(target), **field_kwargs))

    if field_type == 'string':
        if not isinstance(default, str):
            raise reject('default must be a string')
        _reject_misplaced_constraints(cfg, reject, allow_length=True)
        return (str, Field(default=default, **length_constraints(), **field_kwargs))

    if field_type == 'boolean':
        if not isinstance(default, bool):
            raise reject('default must be a boolean')
        _reject_misplaced_constraints(cfg, reject)
        return (bool, Field(default=default, **field_kwargs))

    if field_type == 'color':
        if not isinstance(default, str) or not _COLOR_RE.match(default):
            raise reject('default must be a #RRGGBB or #RRGGBBAA color')
        _reject_misplaced_constraints(cfg, reject)
        return (str, Field(default=default, **field_kwargs))

    # select
    if not cfg.options:
        raise reject('select type requires non-empty options')
    if default not in cfg.options:
        raise reject('default must be one of the options')
    _reject_misplaced_constraints(cfg, reject)
    return (Literal[tuple(cfg.options)], Field(default=default, **field_kwargs))


class _ReadOnlyConfig:
    """模板配置的只读点号访问包装（禁止模板修改 config）。"""

    def __init__(self, data: dict) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in self._data:
            raise AttributeError(name)
        return _wrap_readonly(self._data[name])

    def __getitem__(self, key: str) -> Any:
        return _wrap_readonly(self._data[key])

    def __repr__(self) -> str:
        return f'<config {self._data!r}>'


def _wrap_readonly(value: Any) -> Any:
    """递归包装 dict/list 为只读访问结构。"""
    if isinstance(value, dict):
        return _ReadOnlyConfig(value)
    if isinstance(value, list):
        return [_wrap_readonly(item) for item in value]
    return value


@dataclass(frozen=True)
class TemplateRegistration:
    """template 无代码扩展的注册记录。"""

    extension_id: str  # 与清单 id 一致，也是 config_store 的存储 id
    templates_dir: Path  # [template].entry 解析出的模板根目录
    resource_ids: tuple[str, ...]  # [template].resources 声明的资源扩展 id
    config_model: type[BaseModel]  # 由 config_schema 编译的受限 Pydantic 模型
    config_store: ExtensionConfigStore  # 独立配置存储（Config/Extensions/<id>.toml）


@dataclass(frozen=True)
class OnlineAsset:
    """在线资源包装：扩展在上下文中用它标记在线 URL，由渲染器决定如何引用。"""

    url: str

    def __str__(self) -> str:
        """按当前渲染器转换为可用字符串（未激活渲染器时原样返回 URL）。"""
        return _resolve_asset_str(self)


@dataclass(frozen=True)
class FileAsset:
    """本地文件资源包装：扩展在上下文中用它标记本地文件，由渲染器决定如何引用。"""

    path: Path

    def __str__(self) -> str:
        """按当前渲染器转换为可用字符串（未激活渲染器时返回磁盘路径）。"""
        return _resolve_asset_str(self)


# 当前渲染中的激活渲染器（供 Jinja2 资源函数把包装转换为渲染器可用字符串）。
# 用 ContextVar 而非模块级变量：并发渲染时各任务上下文隔离，避免互相覆盖
_current_renderer: ContextVar[BaseRenderer | None] = ContextVar('current_renderer', default=None)


def _resolve_asset_str(asset: OnlineAsset | FileAsset) -> str:
    """把资源包装按当前激活渲染器转换为字符串。"""
    renderer = _current_renderer.get()
    if isinstance(asset, OnlineAsset):
        return asset.url if renderer is None else renderer.deal_online_asset(asset)
    if isinstance(asset, FileAsset):
        return str(asset.path) if renderer is None else renderer.deal_file_asset(asset)
    return str(asset)


class BaseRenderer:
    """渲染引擎基类，所有渲染扩展必须实现。"""

    name: str = ''

    async def setup(self) -> None:
        """初始化（启动浏览器/加载资源等）。"""

    async def render(self, html_content: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        """渲染为 PNG 字节。

        size: (宽度, 高度)；高度为 0/None 表示按内容自适应。
        """
        raise NotImplementedError

    async def shutdown(self) -> None:
        """清理资源。"""

    def deal_online_asset(self, asset: OnlineAsset) -> str:
        """把在线资源包装转换为本渲染器可用的字符串（默认原样返回 URL）。"""
        return asset.url

    def deal_file_asset(self, asset: FileAsset) -> str:
        """把本地文件包装转换为本渲染器可用的字符串（默认返回磁盘路径）。"""
        return str(asset.path)


class RendererRegistry:
    """渲染器注册表：收集 renderer 引擎实例。"""

    def __init__(self, manager: ExtensionManager) -> None:
        self._manager = manager

    def register(self, renderer: BaseRenderer) -> None:
        """注册一个渲染引擎实例。"""
        self._manager.register_renderer(renderer)


class RendererManager:
    """统一管理渲染引擎与模板/资源注册，负责编排渲染与引擎并发/超时。"""

    def __init__(self, get_renderer_factory: Callable[[str], BaseRenderer | None]) -> None:
        # 从扩展管理器获取渲染引擎实例的函数：name -> BaseRenderer | None
        self._get_renderer = get_renderer_factory
        # 已 setup 的引擎实例：name -> BaseRenderer
        self._active: dict[str, BaseRenderer] = {}
        # 各引擎并发上限与单次渲染超时（秒）
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._timeouts: dict[str, float] = {}
        self._default_timeout = 60.0
        # 模板与资源注册表（由扩展管理器提交）
        self.templates: dict[str, TemplateRegistration] = {}
        self.resources: dict[str, Path] = {}
        # Jinja2 环境缓存：extension_id -> Environment | None（None 表示待重建）
        self._environments: dict[str, Environment | None] = {}

    # ---------- 注册接口 ----------

    def register_template(self, registration: TemplateRegistration) -> None:
        """注册 template 无代码扩展；重复注册覆盖并失效缓存。"""
        self.templates[registration.extension_id] = registration
        self._environments.pop(registration.extension_id, None)
        logger.info(f'Template extension {registration.extension_id} registered.')

    def unregister_template(self, extension_id: str) -> None:
        """注销 template 扩展并清理缓存。"""
        self.templates.pop(extension_id, None)
        self._environments.pop(extension_id, None)

    def register_resources(self, extension_id: str, resources_dir: Path) -> None:
        """注册 resources 无代码扩展。"""
        self.resources[extension_id] = resources_dir
        logger.info(f'Resource extension {extension_id} registered.')

    def unregister_resources(self, extension_id: str) -> None:
        """注销 resources 扩展。"""
        self.resources.pop(extension_id, None)

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
        registration = self.templates.get(template_id)
        if registration is not None:
            loaders.append(FileSystemLoader(str(registration.templates_dir)))
        # 默认模板扩展作为最终回退
        default_reg = self.templates.get('default')
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

    def _select_template(self) -> TemplateRegistration:
        """
        按 `config.image.template` 选择模板包；缺失时回退默认模板。

        回退顺序：config 指定模板 -> 兼容旧配置的 'default' 注册 -> 首个注册模板。
        """
        template_id = (config.image.template or '').strip() or 'Default'
        registration = self.templates.get(template_id)
        if registration is not None:
            return registration
        fallback = self.templates.get('default')
        if fallback is None and self.templates:
            fallback = next(iter(self.templates.values()))
        if fallback is None:
            raise RuntimeError(
                'No usable template extension found, please make sure the default template extension is enabled!'
            )
        logger.warning(
            f'Template extension {template_id} not found, falling back to default template {fallback.extension_id}.'
        )
        return fallback

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

    def _load_style(self, environment: Environment, name: str, **context):
        """加载 base.css + 模板专属 css，并通过 Jinja2 异步渲染。"""

        async def _render() -> str:
            parts = []
            for css_name in ('Base.css', f'{name}/{name}.css'):
                try:
                    template = environment.get_template(css_name)
                    parts.append(await template.render_async(**context))
                except TemplateNotFound:
                    continue
            return '\n'.join(parts)

        return _render()

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
        for root in self.resources.values():
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
        root = self.resources.get(extension_id)
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
        root = self.resources.get(extension_id)
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
        """
        registration = self._select_template()
        environment = self._get_environment(registration.extension_id)
        # 资源依赖检查
        missing = [rid for rid in registration.resource_ids if rid not in self.resources]
        if missing:
            raise ExtensionError(
                f'template {registration.extension_id} declares unregistered resource extensions: {missing}'
            )
        # 解析渲染引擎：先激活，供资源包装转换使用
        renderer_name = renderer or config.image.renderer
        active_renderer = self._active.get(renderer_name)
        if active_renderer is None:
            active_renderer = await self.setup(renderer_name)
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
        active_renderer: BaseRenderer | None,
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
        font_uri = (
            active_renderer.deal_file_asset(FileAsset(font_path)) if active_renderer is not None else str(font_path)
        )
        injected = {
            'config': await self._config_context(registration),
            'width': width,
            'height': height,
            'font_uri': font_uri,
        }
        merged = {**injected, **user_context}
        # 渲染 HTML 与 CSS
        try:
            html_template = environment.get_template(f'{template}/{template}.html')
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
            active_renderer.name if active_renderer else '',
            (width, height),
        )

    # ---------- 引擎管理 ----------

    def configure(self, name: str, concurrency: int = 1, timeout: float | None = None) -> None:
        """配置指定引擎的并发上限与单次渲染超时。"""
        self._semaphores[name] = asyncio.Semaphore(max(1, concurrency))
        if timeout is not None:
            self._timeouts[name] = timeout

    async def setup(self, name: str) -> BaseRenderer | None:
        """初始化并启用指定引擎，未选择或不存在时返回 None。"""
        if not name:
            logger.error('No render engine selected!')
            return None
        renderer = self._get_renderer(name)
        if renderer is None:
            logger.error(f'Render engine {name} does not exist!')
            return None
        if name in self._active:
            return renderer
        await renderer.setup()
        self._active[renderer.name] = renderer
        if renderer.name not in self._semaphores:
            # 默认并发 = 1：渲染引擎（浏览器内核等）通常不支持并发页面安全复用
            self._semaphores[renderer.name] = asyncio.Semaphore(1)
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
