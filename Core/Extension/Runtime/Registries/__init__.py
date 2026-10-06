"""扩展框架·注册表子包（Registries）：纯注册容器。

每种扩展类型一份注册表，只负责「有什么」（增删查清），不承担校验、构建、
渲染或生命周期编排——那些属于同级 `Managers/` 子包。`ExtensionRegistries`
（Bundle）集中全部容器（扩展本体 + 服务 / 命令 / 渲染器 / 模板 / 资源），
由 `ExtensionManager` 创建后按引用交给 Loader 与各管理器。

依赖方向：`Managers/` → `Registries/`（管理器读写下层容器），注册表不反向依赖管理器。
"""

from .Bundle import ExtensionRegistries
from .Command import CommandRegistry
from .Extension import ExtensionRegistry
from .Renderer import RendererRegistry
from .Resources import ResourcesRegistry
from .Service import ServiceRegistry
from .Template import TemplateRegistry

__all__ = [
    'CommandRegistry',
    'ExtensionRegistries',
    'ExtensionRegistry',
    'RendererRegistry',
    'ResourcesRegistry',
    'ServiceRegistry',
    'TemplateRegistry',
]
