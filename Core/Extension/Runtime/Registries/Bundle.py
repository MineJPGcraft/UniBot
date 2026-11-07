"""
扩展框架注册表集合（Bundle）。

集中六类纯容器（扩展本体 / 服务 / 命令 / 渲染器 / 模板 / 资源），由 `ExtensionManager`
创建后按引用交给 `ExtensionLoader` 与各管理器（命令容器交给 `CommandManager`）。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

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

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """声明失败时恢复能力登记及归属，保留原有对象和容器引用。"""
        services = self.services.all()
        service_owners = {name: self.services.owner_of(name) for name in services}
        commands = self.commands.all()
        command_owners = {name: self.commands.owner_of(name) for name in commands}
        renderers = self.renderers.all()
        renderer_owners = {name: self.renderers.owner_of(name) for name in renderers}
        templates = self.templates.all()
        resources = self.resources.all()
        try:
            yield
        except BaseException:
            self.services.clear()
            self.commands.clear()
            self.renderers.clear()
            self.templates.clear()
            self.resources.clear()
            for name, service in services.items():
                self.services.register(name, service, owner_id=service_owners[name])
            for name, command in commands.items():
                self.commands.register(name, command, owner_id=command_owners[name])
            for name, renderer in renderers.items():
                self.renderers.register(renderer, owner_id=renderer_owners[name])
            for registration in templates.values():
                self.templates.register(registration)
            for extension_id, directory in resources.items():
                self.resources.register(extension_id, directory)
            raise
