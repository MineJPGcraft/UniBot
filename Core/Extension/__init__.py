"""UniBot 扩展系统框架包（大部分模块置于本层，仅运行时引擎收进 `Runtime/`；包根统一 re-export）。

布局：
- 本层（`Core/Extension/`）：定义与基类模块——`Errors`、`Manifest`、`Storage`、
  `TemplateConfig`、`Base`（Extension 基类/状态机）、`Command`、`Service`、`Renderer`
- `Runtime/`：运行时引擎——`Host`（Protocol）、`Registry`、`Dependencies`、`Loader`、
  `Manager`、`Market`、`MarketManager`

依赖方向单向：`Runtime/` → 本层模块；本层不导入 `Runtime/` 实现
（仅 `TYPE_CHECKING` 引用 `Host` 作类型注解）。

注：顶层采用即时导入（包名与子模块名存在同名类，如 `Command`/`Service`，
惰性导出会因子模块属性覆盖同名类而造成歧义，故此处保持即时导入）。
"""

from nonebot_plugin_alconna import Match

from Core.Constants import CONFIG_EXTENSIONS_FILE, EXTENSIONS_DIR, MANIFEST_FILE

from .Base import (
    Extension,
    ExtensionState,
)
from .Command import (
    UNSET,
    Argument,
    Command,
    CommandManager,
    Handler,
    ImageHandler,
    SubCommand,
    command_manager,
)
from .Errors import (
    CommandError,
    CommandFieldError,
    CompatibilityError,
    DependencyError,
    ExtensionError,
    ExtensionNotBoundError,
    LoadError,
    ManifestError,
    StorageError,
)
from .Manifest import (
    ExtensionManifest,
    ExtensionMetadata,
    ExtensionType,
    get_unibot_version,
    is_unibot_compatible,
    manifest_from_attributes,
    parse_manifest,
    set_unibot_version,
)
from .Renderer import (
    FONT_PATH,
    RESOURCES_DIR,
    BaseRenderer,
    FileAsset,
    OnlineAsset,
    RendererManager,
    RendererRegistry,
    TemplateRegistration,
    encode_context,
)
from .Runtime.Loader import (
    BUILTIN_DIR,
    CONFIG_ROOT,
    DATA_ROOT,
    STATES_FILE,
    STATES_ROOT,
    ExtensionLoader,
)
from .Runtime.Manager import ExtensionManager, extension_manager
from .Runtime.Market import (
    ExtensionInstallState,
    MarketExtension,
    MarketRelease,
    extract_market_package,
)
from .Runtime.MarketManager import ExtensionMarketManager, InstallResult, MarketReleaseOption, market_manager
from .Service import Service, ServiceRegistry
from .Storage import (
    RESERVED_STATE_FILE,
    ExtensionConfigStore,
    ExtensionDataStore,
)
from .TemplateConfig import build_template_config_model

__all__ = [
    # Alconna
    'Match',
    # Base
    'CompatibilityError',
    'DependencyError',
    'Extension',
    'ExtensionError',
    'ExtensionManifest',
    'ExtensionMetadata',
    'ExtensionNotBoundError',
    'ExtensionState',
    'ExtensionType',
    'LoadError',
    'ManifestError',
    'StorageError',
    'get_unibot_version',
    'is_unibot_compatible',
    'manifest_from_attributes',
    'parse_manifest',
    'set_unibot_version',
    # Command
    'Argument',
    'Command',
    'CommandError',
    'CommandFieldError',
    'CommandManager',
    'Handler',
    'ImageHandler',
    'SubCommand',
    'UNSET',
    'command_manager',
    # Constants
    'CONFIG_EXTENSIONS_FILE',
    'EXTENSIONS_DIR',
    'MANIFEST_FILE',
    # Loader
    'BUILTIN_DIR',
    'CONFIG_ROOT',
    'DATA_ROOT',
    'ExtensionLoader',
    'STATES_FILE',
    'STATES_ROOT',
    # Manager
    'ExtensionManager',
    'extension_manager',
    # Market
    'ExtensionInstallState',
    'MarketExtension',
    'MarketRelease',
    'extract_market_package',
    # MarketManager
    'ExtensionMarketManager',
    'InstallResult',
    'MarketReleaseOption',
    'market_manager',
    # Service
    'Service',
    'ServiceRegistry',
    # Renderer
    'BaseRenderer',
    'FONT_PATH',
    'FileAsset',
    'OnlineAsset',
    'RESOURCES_DIR',
    'RendererManager',
    'RendererRegistry',
    'TemplateRegistration',
    'build_template_config_model',
    'encode_context',
    # Storage
    'ExtensionConfigStore',
    'ExtensionDataStore',
    'RESERVED_STATE_FILE',
]
