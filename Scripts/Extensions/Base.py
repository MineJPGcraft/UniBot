"""UniBot 扩展系统：扩展基类、元数据、状态机。"""

from __future__ import annotations

import tomllib
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from Scripts.Logging import logger
from Scripts.Managers import config_manager

from .Command import Command
from .Errors import (
    ExtensionError,
    ExtensionNotBoundError,
    ManifestError,
)
from .Service import ServiceRegistry
from .Storage import ExtensionConfigStore, ExtensionDataStore

CommandClassT = TypeVar('CommandClassT', bound='Command')
ServiceClassT = TypeVar('ServiceClassT')
RendererClassT = TypeVar('RendererClassT')
ConfigModelT = TypeVar('ConfigModelT', bound=BaseModel)


class ExtensionState(StrEnum):
    """扩展生命周期状态。"""

    discovered = 'discovered'  # 发现目录，尚未校验
    validated = 'validated'  # 清单校验通过
    loaded = 'loaded'  # 模块导入并完成声明
    enabled = 'enabled'  # 已启用（on_enable 完成）
    disabled = 'disabled'  # 管理员主动禁用
    blocked = 'blocked'  # 依赖禁用/失败导致不可用
    failed = 'failed'  # 加载或启用失败


# 允许的状态迁移：状态 -> 可达状态集合
_STATE_TRANSITIONS: dict[ExtensionState, set[ExtensionState]] = {
    ExtensionState.discovered: {ExtensionState.validated, ExtensionState.failed},
    ExtensionState.validated: {ExtensionState.loaded, ExtensionState.failed},
    ExtensionState.loaded: {ExtensionState.enabled, ExtensionState.disabled, ExtensionState.failed},
    ExtensionState.enabled: {ExtensionState.disabled, ExtensionState.failed},
    ExtensionState.disabled: {ExtensionState.enabled, ExtensionState.failed},
    ExtensionState.blocked: {ExtensionState.enabled, ExtensionState.failed},
    ExtensionState.failed: set(),
}


# ===== 清单元数据（extension.toml） =====


class ExtensionType(StrEnum):
    """扩展类型。

    `api`/`command`/`renderer` 为代码型能力；`template`/`resources` 为无代码扩展包。
    """

    api = 'api'
    command = 'command'
    renderer = 'renderer'
    template = 'template'
    resources = 'resources'


# 无代码扩展包只能单独成包，不能与任何代码能力混用
_CODE_TYPES = {ExtensionType.api, ExtensionType.command, ExtensionType.renderer}
_NO_CODE_TYPES = {ExtensionType.template, ExtensionType.resources}


class ManifestMeta(BaseModel):
    """[manifest] 段：清单格式版本。"""

    model_config = ConfigDict(extra='forbid')

    schema_version: int = 1


class ExtensionMeta(BaseModel):
    """[extension] 段：扩展身份信息。"""

    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1, pattern=r'^[A-Za-z0-9_]+$')
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    author: str = ''
    description: str = ''
    types: list[ExtensionType] = [ExtensionType.api]


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
        """校验类型互斥：无代码类型（template/resources）不能与代码能力混用，renderer 独立成包。"""
        types = set(self.extension.types)
        no_code = types & _NO_CODE_TYPES
        code = types & _CODE_TYPES
        if no_code and code:
            raise ValueError(
                f'No-code extension types {sorted(t.value for t in no_code)} '
                f'cannot be mixed with code capabilities {sorted(t.value for t in code)}!'
            )
        if types == {ExtensionType.renderer} and not self.renderer.name:
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
        """是否为无代码扩展包（template/resources）。"""
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


# ===== Extension 基类 =====


class Extension(Generic[ConfigModelT]):
    """
    UniBot 本地扩展基类，所有扩展必须继承并实现。

        扩展通过实例装饰器 `@extension.register_command` / `@extension.register_service`
        / `@extension.register_renderer` 把能力类登记到该实例。装饰器只记录声明，
        由 Loader 实例化并提交，不产生全局注册副作用。

        `Extension()` 采用两阶段绑定：模块导入期间构造的是 unbound 实例，只允许读取
        `config_model` 和使用三个注册装饰器；`metadata`、`config`、`data`、`api`、
        `logger` 在此阶段访问应抛出 `ExtensionNotBoundError`。Loader 校验入口与清单后
        调用内部 `_bind()` 一次性注入这些能力并将状态切换为 bound；扩展代码不能直接
        调用 `_bind()`，重复绑定必须失败。
    """

    # 公开元数据类属性（单文件扩展由类属性声明，多文件扩展以 Extension.toml 为准）
    name: str = ''
    version: str = ''
    author: str = ''
    description: str = ''
    types: tuple[str, ...] = ()

    # 由扩展类声明，Loader 实例化后注入；实例上始终非 None（缺省用空配置模型）
    config_model: type[ConfigModelT] | None = None

    logger = logger

    state: ExtensionState = ExtensionState.discovered

    # 失败原因（mark_failed 时记录）
    failure_reason: str | None = None

    # 是否为随框架分发的内置扩展（Builtin/ 目录，加载时由 Loader 标记）
    builtin: bool = False

    # 私有状态：id 声明值（未绑定前生效）与绑定标志
    _declared_id: str = ''
    _bound: bool = False

    def __init__(
        self,
        *,
        id: str = '',
        name: str = '',
        version: str = '',
        author: str = '',
        description: str = '',
        types: tuple[str, ...] = (),
        config_model: type[ConfigModelT] | None = None,
    ) -> None:
        """
        初始化扩展实例。只能登记能力类，不能产生全局注册副作用。

                元数据可直接通过构造参数声明（`Extension(id='List', name='...')`），
                也可由单文件扩展在子类上用类属性声明；两者等价，Loader 统一归一化。
                多文件扩展的元数据以 `Extension.toml` 为准，无需在此传入 id。
        """
        # 能力声明集合为实例私有，避免多个实例共享同一 list 导致互相污染
        self.commands: list = []
        self.services: list = []
        self.renderers: list = []
        self._metadata: ExtensionMetadata | None = None
        self._config: ExtensionConfigStore[ConfigModelT] | None = None
        self._data: ExtensionDataStore | None = None
        self._api: ServiceRegistry | None = None
        # 构造参数优先，缺省沿用类属性声明
        # 注意：id 通过 _declared_id 写入而非 id property，
        # 因为子类可能把 id 重新定义为只读 property（见测试 _GoodExt）
        self._declared_id = id or self._declared_id
        self.name = name or self.name
        self.version = version or self.version
        self.author = author or self.author
        self.description = description or self.description
        self.types = types or self.types
        self.config_model = config_model or self.config_model or cast(type[ConfigModelT], self._default_config_model())

    # ===== 公开属性 =====

    @property
    def id(self) -> str:
        """扩展唯一标识：绑定后来自 metadata，未绑定来自声明值。"""
        if self._metadata is not None:
            return self._metadata.id
        return self._declared_id

    @id.setter
    def id(self, value: str) -> None:
        self._declared_id = value

    @property
    def is_bound(self) -> bool:
        """返回扩展是否已完成能力绑定。"""
        return self._bound

    @property
    def metadata(self) -> ExtensionMetadata:
        """返回扩展元数据，尚未完成发现时抛出明确错误。"""
        if self._metadata is None:
            raise ExtensionNotBoundError(f'Extension {self.id or "<unknown>"} has no metadata yet!')
        return self._metadata

    @property
    def config(self) -> ExtensionConfigStore[ConfigModelT]:
        """返回当前扩展的配置存储，未绑定时抛出明确错误。"""
        self._require_bound()
        assert self._config is not None
        return self._config

    @property
    def data(self) -> ExtensionDataStore:
        """返回当前扩展的数据存储，未绑定时抛出明确错误。"""
        self._require_bound()
        assert self._data is not None
        return self._data

    @property
    def api(self) -> ServiceRegistry:
        """返回当前扩展的服务注册表，未绑定时抛出明确错误。"""
        self._require_bound()
        assert self._api is not None
        return self._api

    # ===== 声明提交（实例装饰器，能力归属由装饰时使用的实例决定） =====

    def register_command(self, command_cls: type[CommandClassT]) -> type[CommandClassT]:
        """实例装饰器：登记一个 Command 子类，返回该类（保留类型信息）。"""
        self.commands.append(command_cls)
        return command_cls

    def register_service(self, service_cls: type[ServiceClassT]) -> type[ServiceClassT]:
        """实例装饰器：登记一个 Service 子类，返回该类。"""
        self.services.append(service_cls)
        return service_cls

    def register_renderer(self, renderer_cls: type[RendererClassT]) -> type[RendererClassT]:
        """实例装饰器：登记一个 BaseRenderer 子类，返回该类（保留类型信息）。"""
        self.renderers.append(renderer_cls)
        return renderer_cls

    # ===== 配置工具 =====

    @property
    def config_value(self) -> ConfigModelT:
        """返回已绑定的配置模型（未绑定时抛出明确错误）。"""
        return self.config.value

    def get_config_schema(self) -> dict:
        """返回扩展配置的 JSON Schema（供 WebUI 动态生成表单）。"""
        assert self.config_model is not None
        return self.config_model.model_json_schema()

    def update_config(self, values: dict) -> BaseModel:
        """校验并持久化配置；校验失败抛出异常且不修改原配置。"""
        return self.config.update(values)

    async def render_image(
        self,
        template: str,
        size: tuple[int, int],
        *,
        context: dict | None = None,
        renderer: str | None = None,
    ) -> bytes:
        """
        使用当前选中的模板包配置和渲染系统生成图片。

            只做受控转发到框架注入的 `RendererManager`。模板包由核心
            `config.image.template` 选择，`template` 参数表示包内模板名称
            （如 `List`）。Jinja 上下文中的 `config` 始终来自当前 template
            包，与调用方代码扩展配置无关。
        """
        self._require_bound()
        # 函数内导入：避免导入期循环依赖（Scripts.Extensions 初始化顺序）
        from Scripts.Extensions import extension_manager

        return await extension_manager.renderer_manager.render_image(
            template,
            size,
            context=context,
            renderer=renderer,
        )

    # ===== 生命周期 =====

    async def on_load(self) -> None:
        """实例创建后、声明完成后调用（可选覆盖）。"""

    async def on_enable(self) -> None:
        """声明确认后启动外部资源（可选覆盖）。"""

    async def on_disable(self) -> None:
        """释放外部资源（可选覆盖）。"""

    # ===== 两阶段绑定（Loader 内部调用） =====

    @staticmethod
    def _default_config_model() -> type[BaseModel]:
        """未声明 config_model 时使用空配置模型，不接受未声明字段。"""

        class EmptyConfig(BaseModel):
            model_config = ConfigDict(extra='forbid')

        return EmptyConfig

    def _bind(
        self,
        metadata: ExtensionMetadata,
        config_store: ExtensionConfigStore[ConfigModelT],
        data_store: ExtensionDataStore,
        api: ServiceRegistry,
        *,
        builtin: bool = False,
    ) -> None:
        """Loader 一次性注入绑定能力；只能调用一次，扩展代码不得直接调用。"""
        if self._bound:
            raise ExtensionError(f'Extension {self.id} bound twice!')
        self._metadata = metadata
        self._config = config_store
        self._data = data_store
        self._api = api
        self.builtin = builtin
        self._bound = True

    def _set_metadata(self, metadata: ExtensionMetadata) -> None:
        """为未加载的展示实例注入元数据。"""
        self._metadata = metadata

    def _require_bound(self) -> None:
        """访问绑定能力前校验是否已绑定，否则抛错。"""
        if not self._bound:
            raise ExtensionNotBoundError(f'Extension {self.id or "<unknown>"} is not bound yet, cannot access this capability!')

    # ===== 状态机 =====

    def transition(self, target: ExtensionState) -> None:
        """按状态机迁移扩展状态，非法迁移抛出错误。"""
        allowed = _STATE_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise ExtensionError(f'Extension {self.id} invalid state transition: {self.state.value} -> {target.value}')
        self.state = target

    def mark_failed(self, reason: str) -> None:
        """将扩展标记为失败状态，并记录原因。"""
        self.logger.error(f'Extension {self.id} failed to load: {reason}')
        self.state = ExtensionState.failed
        self.failure_reason = reason


def get_unibot_version() -> str:
    """获取当前 UniBot 版本号（去除前缀 v）。"""
    return config_manager.version.lstrip('v')
