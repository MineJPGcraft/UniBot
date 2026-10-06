"""UniBot 扩展系统框架包（根为定义层，`Runtime/` 与 `Market/` 为子包；包根统一 re-export）。

布局（判据：扩展作者会不会 import 它——会则根，不会则子包）：
- 根（`Core/Extension/`）：定义与基类——`Extension`（Extension 基类/状态机）、
  `Command`、`Service`、`Renderer`、`Errors`、`Manifest`、`Storage`、`TemplateConfig`
- `Runtime/`：运行时引擎——`Loader`、`Dependencies`，另含两个组件子包：
  `Registries/`（扩展本体与五类能力的纯注册容器）与 `Managers/`（对应管理器与编排）
- `Market/`：扩展市场——`Models.py`（数据形状）+ `Manager.py`（缓存、解压与安装/卸载事务 + `market_manager`）

依赖方向严格单向：根 → `Runtime/` → `Market/`（由 `tests/test_architecture.py` 锁定）。
运行时组件由 `ExtensionManager` 创建后按引用传入 `ExtensionLoader`，不使用回调注入。

注：顶层采用即时导入（包名与子模块名存在同名类，如 `Command`/`Service`，
惰性导出会因子模块属性覆盖同名类而造成歧义，故此处保持即时导入）。
"""

from nonebot_plugin_alconna import Match

from Core.Constants import CONFIG_EXTENSIONS_FILE, EXTENSIONS_DIR, MANIFEST_FILE, STATES_PATH

from .Command import (
    UNSET,
    Argument,
    Command,
    Handler,
    ImageHandler,
    SubCommand,
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
from .Extension import (
    Extension,
    ExtensionState,
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
from .Market import (
    ExtensionInstallState,
    ExtensionMarketManager,
    MarketExtension,
    MarketOperationResult,
    MarketRelease,
    extract_market_package,
    market_manager,
)
from .Renderer import (
    FONT_PATH,
    RESOURCES_DIR,
    BaseRenderer,
    FileAsset,
    OnlineAsset,
    TemplateRegistration,
    encode_context,
)
from .Runtime.Loader import (
    BUILTIN_DIR,
    CONFIG_ROOT,
    DATA_ROOT,
    ExtensionLoader,
)
from .Runtime.Manager import ExtensionManager, extension_manager
from .Runtime.Managers import CommandManager, RendererManager, ServiceManager
from .Runtime.Registries import ExtensionRegistries, ServiceRegistry
from .Service import Service
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
    # Constants
    'CONFIG_EXTENSIONS_FILE',
    'EXTENSIONS_DIR',
    'MANIFEST_FILE',
    'STATES_PATH',
    # Loader
    'BUILTIN_DIR',
    'CONFIG_ROOT',
    'DATA_ROOT',
    'ExtensionLoader',
    # Manager
    'ExtensionManager',
    'extension_manager',
    # Managers / Registries
    'ServiceManager',
    'ExtensionRegistries',
    'ServiceRegistry',
    # Market
    'ExtensionInstallState',
    'ExtensionMarketManager',
    'MarketExtension',
    'MarketOperationResult',
    'MarketRelease',
    'extract_market_package',
    'market_manager',
    # Service
    'Service',
    # Renderer
    'BaseRenderer',
    'FONT_PATH',
    'FileAsset',
    'OnlineAsset',
    'RESOURCES_DIR',
    'RendererManager',
    'TemplateRegistration',
    'build_template_config_model',
    'encode_context',
    # Storage
    'ExtensionConfigStore',
    'ExtensionDataStore',
    'RESERVED_STATE_FILE',
]
