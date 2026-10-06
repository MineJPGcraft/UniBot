"""
扩展框架注册表集合（Bundle）。

集中六类纯容器（扩展本体 / 服务 / 命令 / 渲染器 / 模板 / 资源），由 `ExtensionManager`
创建后按引用交给 `ExtensionLoader` 与各管理器（命令容器交给 `CommandManager`）。
"""

from __future__ import annotations

from .Command import CommandRegistry
from .Extension import ExtensionRegistry
from .Renderer import RendererRegistry
from .Resources import ResourcesRegistry
from .Service import ServiceRegistry
from .Template import TemplateRegistry


class ExtensionRegistries:
    """扩展框架的注册表集合：扩展本体与五类扩展能力的纯容器。"""

    def __init__(self) -> None:
        self.extensions = ExtensionRegistry()
        self.services = ServiceRegistry()
        self.commands = CommandRegistry()
        self.renderers = RendererRegistry()
        self.templates = TemplateRegistry()
        self.resources = ResourcesRegistry()
