"""扩展框架·市场（Market）子包：注册表模型、安全解压与安装/卸载事务。

市场扩展从 GitHub Release 以源码 zip 分发。本子包单向依赖 `Runtime/`（Loader 常量
与全局扩展管理器单例）与本层（`../`）的定义/错误/清单模块。对外唯一出口即本模块：
`Models.py` 提供数据形状（Pydantic 模型与市场视图对象），`Manager.py` 提供注册表缓存、
安装状态持久化与安全安装/卸载事务。
"""

from .Manager import ExtensionMarketManager, extract_market_package, market_manager
from .Models import (
    ExtensionInstallState,
    MarketExtension,
    MarketOperationResult,
    MarketRelease,
)

__all__ = [
    'ExtensionInstallState',
    'ExtensionMarketManager',
    'MarketExtension',
    'MarketOperationResult',
    'MarketRelease',
    'extract_market_package',
    'market_manager',
]
