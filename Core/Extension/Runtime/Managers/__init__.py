"""扩展框架·管理器子包（Managers）：扩展类型的编排层。

每个管理器负责一类扩展的校验、构建、生命周期与运行时读取，状态一律委托给
同级 `Registries/` 的纯容器：

- `Command.py`：`CommandManager` —— 命令校验、Alconna matcher 构建与路由
- `Service.py`：`ServiceManager` —— API 服务实例的启停编排
- `Renderer.py`：`RendererManager` —— 渲染引擎协商、模板环境与渲染流水线

> 扩展总管理器 `ExtensionManager` 是运行时引擎的顶层组合器（创建容器并交给
> `Loader`），位于上一级 `Runtime/Manager.py`，不在本子包内。

子包之外统一 `from .Runtime.Managers import X`（本包即时导出）；`Runtime/Loader.py`
与子包内模块间引用走**直接子模块导入**（如 `from .Command import CommandManager`）。
"""

from .Command import CommandManager
from .Renderer import RendererManager
from .Service import ServiceManager

__all__ = [
    'CommandManager',
    'RendererManager',
    'ServiceManager',
]
