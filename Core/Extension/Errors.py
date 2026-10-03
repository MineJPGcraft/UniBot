"""
UniBot 扩展系统错误模型。

所有扩展相关的异常统一在此定义，按用途分组：
- 通用基类：`ExtensionError`
- 清单/兼容性/依赖/加载/存储：清单解析、版本兼容、依赖拓扑、模块导入、配置读写
- 绑定：在扩展实例绑定前访问受绑定能力
- 命令：命令定义或构建阶段的声明错误。
"""

__all__ = [
    'CompatibilityError',
    'CommandError',
    'CommandFieldError',
    'DependencyError',
    'ExtensionError',
    'ExtensionNotBoundError',
    'LoadError',
    'ManifestError',
    'StorageError',
]


class ExtensionError(Exception):
    """扩展系统错误基类。"""


# ===== 清单 / 兼容性 / 依赖 / 加载 / 存储 =====


class ManifestError(ExtensionError):
    """清单元数据解析或校验失败。"""


class CompatibilityError(ExtensionError):
    """扩展与当前 UniBot 版本不兼容。"""


class DependencyError(ExtensionError):
    """扩展依赖缺失或存在循环依赖。"""


class LoadError(ExtensionError):
    """扩展模块导入或初始化失败。"""


class StorageError(ExtensionError):
    """扩展配置或数据读写失败。"""


# ===== 两阶段绑定 =====


class ExtensionNotBoundError(ExtensionError):
    """在扩展实例绑定前访问受绑定能力。"""


# ===== 命令 =====


class CommandError(ExtensionError):
    """命令定义或构建阶段错误。"""


class CommandFieldError(CommandError):
    """命令字段校验错误，包含扩展 id 与字段路径。"""
