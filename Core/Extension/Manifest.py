"""UniBot 扩展清单模型与解析（`Extension.toml` / 单文件类属性）。"""

from __future__ import annotations

import tomllib
from contextvars import ContextVar
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from packaging.specifiers import SpecifierSet
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .Errors import CompatibilityError, ManifestError

if TYPE_CHECKING:
    from .Base import Extension


class ExtensionType(StrEnum):
    """扩展类型。

    `api`/`command`/`renderer` 为代码型能力；`template`/`resources` 为无代码扩展包；
    两者可自由组合在同一个扩展中。
    """

    api = 'api'
    command = 'command'
    renderer = 'renderer'
    template = 'template'
    resources = 'resources'


# 代码能力与无代码扩展包类型，同一扩展可同时声明两类
_CODE_TYPES = {ExtensionType.api, ExtensionType.command, ExtensionType.renderer}
_NO_CODE_TYPES = {ExtensionType.template, ExtensionType.resources}


class ManifestMeta(BaseModel):
    """[manifest] 段：清单格式版本。"""

    model_config = ConfigDict(extra='forbid')

    schema_version: int = 1


class ExtensionMeta(BaseModel):
    """[extension] 段：扩展身份信息。

    `name` / `description` 允许是 `DeferredText`（延迟求值译文）：内置扩展在注册期
    传入 I18n 引用，展示期 `str()` 才按当前语言解析，故 `name` 校验放宽为
    「非空字符串或 DeferredText」。
    """

    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1, pattern=r'^[A-Za-z0-9_]+$')
    name: object
    version: str = Field(min_length=1)
    author: str = ''
    description: object = ''
    types: list[ExtensionType] = [ExtensionType.api]

    @field_validator('name')
    @classmethod
    def _validate_name(cls, value: object) -> object:
        """name 必须是非空字符串或 DeferredText（延迟求值译文）。"""
        # 函数内导入：避免 Manifest（Foundation）在模块加载期依赖 I18n 的导入顺序
        from Core.I18n import DeferredText

        if isinstance(value, DeferredText):
            return value
        if isinstance(value, str) and value:
            return value
        raise ValueError('name must be a non-empty string or DeferredText!')


class CompatibilityConfig(BaseModel):
    """[compatibility] 段：兼容的机器人版本。"""

    model_config = ConfigDict(extra='forbid')

    unibot: str = '*'


class DependenciesConfig(BaseModel):
    """[dependencies] 段：依赖的其他扩展与第三方 Python 依赖。"""

    model_config = ConfigDict(extra='forbid')

    extensions: list[str] = []
    python: list[str] = []


class RendererConfig(BaseModel):
    """[renderer] 段（仅 renderer 扩展需要）。"""

    model_config = ConfigDict(extra='forbid')

    name: str = ''  # 渲染器名称，必须与注册的 BaseRenderer.name 一致


class TemplateFieldConfig(BaseModel):
    """[template.config_schema.<name>] 单个受限配置字段。"""

    model_config = ConfigDict(extra='forbid')

    type: Literal['string', 'integer', 'number', 'boolean', 'color', 'select'] = 'string'
    default: Any = None
    title: str = ''
    description: str = ''
    # 数值约束
    min: float | int | None = None
    max: float | int | None = None
    # 字符串约束
    min_length: int | None = None
    max_length: int | None = None
    # select 选项（select 类型必填，且 default 必须包含其中）
    options: list[str] = []


class TemplateConfig(BaseModel):
    """[template] 段（仅 template 无代码扩展需要）。"""

    model_config = ConfigDict(extra='forbid')

    entry: str = 'Templates'  # 模板根目录，固定相对于扩展包根目录
    resources: list[str] = []  # 可选 resources 扩展 id，按声明顺序组成资源查找范围
    config_schema: dict[str, TemplateFieldConfig] = Field(default_factory=dict)


class ResourcesConfig(BaseModel):
    """[resources] 段（仅 resources 无代码扩展需要）。"""

    model_config = ConfigDict(extra='forbid')

    root: str = 'Resources'  # 资源根目录，固定相对于扩展包根目录


class ExtensionManifest(BaseModel):
    """extension.toml 根模型，严格校验（未知字段直接阻止加载）。"""

    model_config = ConfigDict(extra='forbid')

    manifest: ManifestMeta = ManifestMeta()
    extension: ExtensionMeta
    compatibility: CompatibilityConfig = CompatibilityConfig()
    dependencies: DependenciesConfig = DependenciesConfig()
    renderer: RendererConfig = RendererConfig()
    template: TemplateConfig = TemplateConfig()
    resources: ResourcesConfig = ResourcesConfig()

    @model_validator(mode='after')
    def _validate_types(self) -> ExtensionManifest:
        """校验类型声明：代码能力与无代码类型可混用，renderer 必须声明名称。"""
        if ExtensionType.renderer in set(self.extension.types) and not self.renderer.name:
            raise ValueError('renderer extensions must declare name in the [renderer] section!')
        return self


class ExtensionMetadata:
    """从清单解析出的便捷元数据对象，供扩展代码与框架使用。"""

    def __init__(self, manifest: ExtensionManifest) -> None:
        self.manifest = manifest
        extension = manifest.extension
        self.id = extension.id
        self.name = extension.name
        self.version = extension.version
        self.author = extension.author
        self.description = extension.description
        self.types = list(extension.types)
        self.unibot_constraint = manifest.compatibility.unibot
        self.extension_dependencies = list(manifest.dependencies.extensions)
        self.python_dependencies = list(manifest.dependencies.python)
        self.renderer_name = manifest.renderer.name
        self.template_entry = manifest.template.entry
        self.template_resources = list(manifest.template.resources)
        self.template_config_schema = manifest.template.config_schema
        self.resources_root = manifest.resources.root

    @property
    def is_no_code(self) -> bool:
        """是否声明了无代码类型（template/resources）。"""
        return any(entry in _NO_CODE_TYPES for entry in self.types)

    def to_dict(self) -> dict:
        """转换为可序列化字典（供 WebUI 展示）。"""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'description': self.description,
            'types': [entry.value for entry in self.types],
            'unibot': self.unibot_constraint,
            'extension_dependencies': self.extension_dependencies,
            'python_dependencies': self.python_dependencies,
            'renderer': self.renderer_name,
            'template_entry': self.template_entry,
            'template_resources': self.template_resources,
            'resources_root': self.resources_root,
        }


def parse_manifest(content: str) -> ExtensionManifest:
    """解析 extension.toml 文本内容，返回严格校验后的清单。"""
    try:
        data = tomllib.loads(content)
    except Exception as error:
        raise ManifestError(f'Failed to parse extension manifest: {error}') from error
    try:
        return ExtensionManifest.model_validate(data)
    except Exception as error:
        raise ManifestError(f'Extension manifest validation failed: {error}') from error


def manifest_from_attributes(extension: Extension) -> ExtensionManifest:
    """
    从单文件扩展的类属性构建清单（无 Extension.toml 时使用）。

        读取 `id`/`name`/`version`/`author`/`description`/`types` 类属性，
        生成与 `Extension.toml` 等价的清单，供 Loader 统一校验与绑定。
    """
    # id 是普通类属性，单文件扩展在类上声明或构造时传入；未声明时取到缺省空串
    extension_id = extension.id
    if not isinstance(extension_id, str) or not extension_id:
        raise ManifestError('Single-file extensions must declare an id!')
    if not extension.name:
        raise ManifestError(f'Extension {extension_id} must declare a name class attribute!')
    if not extension.version:
        raise ManifestError(f'Extension {extension_id} must declare a version class attribute!')
    try:
        types = [ExtensionType(entry) for entry in extension.types]
    except ValueError as error:
        raise ManifestError(f'Extension {extension_id} has invalid types: {extension.types}') from error
    return ExtensionManifest(
        extension=ExtensionMeta(
            id=extension_id,
            name=extension.name,
            version=extension.version,
            author=extension.author,
            description=extension.description,
            types=types,
        )
    )


# 当前 UniBot 版本号：由 Bootstrap 启动时注入，避免框架层反向依赖 Managers
_version: ContextVar[str] = ContextVar('unibot_version', default='')


def get_unibot_version() -> str:
    """获取当前 UniBot 版本号（去除前缀 v）。"""
    return _version.get()


def set_unibot_version(version: str) -> None:
    """注入当前 UniBot 版本号，供版本兼容校验使用。"""
    _version.set(version)


def unibot_specifier(constraint: str) -> SpecifierSet | None:
    """解析 UniBot 版本约束；空串与 `'*'` 返回 None（表示任意版本）。"""
    if not constraint or constraint == '*':
        return None
    return SpecifierSet(constraint)


def is_unibot_compatible(constraint: str) -> bool:
    """
    判断版本约束是否落在当前 UniBot 版本内（不抛错的判定版）。

    空串 / `'*'` / 非法约束分别处理：空与通配视为兼容，非法约束视为不兼容。
    市场安装用它挑选历史版本，`validate_unibot_constraint` 仍是校验的唯一入口。
    """
    try:
        specifier = unibot_specifier(constraint)
    except Exception:
        return False
    if specifier is None:
        return True
    current_version = get_unibot_version()
    return not current_version or current_version in specifier


def validate_unibot_constraint(extension_id: str, constraint: str) -> None:
    """
    校验扩展声明的 UniBot 版本约束与当前版本兼容，不满足时抛 CompatibilityError。

    Loader 与市场安装共用此实现；`'*'` / 空串表示任意版本。
    """
    try:
        specifier = unibot_specifier(constraint)
    except Exception as error:
        raise CompatibilityError(
            f'Extension {extension_id} has invalid version constraint: {constraint} ({error})'
        ) from error
    if specifier is None:
        return
    current_version = get_unibot_version()
    if current_version and current_version not in specifier:
        raise CompatibilityError(
            f'Extension {extension_id} requires UniBot {constraint}, but current version is {current_version}.'
        )
