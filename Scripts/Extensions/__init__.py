"""UniBot 扩展系统框架包。"""

from nonebot_plugin_alconna import Match

from Scripts.Constants import CONFIG_EXTENSIONS_FILE, EXTENSIONS_DIR, MANIFEST_FILE

from .Base import (
    Extension,
    ExtensionManifest,
    ExtensionMetadata,
    ExtensionState,
    ExtensionType,
    manifest_from_attributes,
    parse_manifest,
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
from .Loader import (
    BUILTIN_DIR,
    CONFIG_ROOT,
    DATA_ROOT,
    STATES_FILE,
    STATES_ROOT,
    ExtensionLoader,
)
from .Manager import ExtensionManager, extension_manager
from .Market import (
    ExtensionInstallState,
    MarketExtension,
    MarketRelease,
    extract_market_package,
)
from .MarketManager import ExtensionMarketManager, market_manager
from .Renderer import (
    FONT_PATH,
    RESOURCES_DIR,
    BaseRenderer,
    FileAsset,
    OnlineAsset,
    RendererManager,
    RendererRegistry,
    TemplateRegistration,
    build_template_config_model,
    encode_context,
)
from .Service import Service, ServiceRegistry
from .Storage import (
    RESERVED_STATE_FILE,
    ExtensionConfigStore,
    ExtensionDataStore,
)

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
    'manifest_from_attributes',
    'parse_manifest',
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
