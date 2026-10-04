"""
扩展框架注册表集合（Bundle）。

集中五个纯容器（扩展 / 服务 / 渲染器 / 模板 / 资源），由 `ExtensionManager` 创建后
按引用交给 `ExtensionLoader` 与各管理器；命令注册表由全局命令管理器
（`Managers/Command.py`）自持，不在此集合内。
"""

from __future__ import annotations

from .Extension import ExtensionRegistry
from .Renderer import RendererRegistry
from .Resources import ResourcesRegistry
from .Service import ServiceRegistry
from .Template import TemplateRegistry


class ExtensionRegistries:
    """扩展框架的注册表集合：五种扩展类型的纯容器。"""

    def __init__(self) -> None:
        self.extensions = ExtensionRegistry()
        self.services = ServiceRegistry()
        self.renderers = RendererRegistry()
        self.templates = TemplateRegistry()
        self.resources = ResourcesRegistry()
