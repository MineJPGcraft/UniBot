"""
扩展框架对宿主的抽象接口。

`ExtensionLoader` / `ServiceRegistry` / `RendererRegistry` 只依赖本 Protocol，
由 `ExtensionManager` 实现，从而打破「Loader ↔ Manager」的相互引用，
使框架内部的依赖方向单向向下（见 Refactor.md §6.2）。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ..Base import Extension
    from ..Renderer import BaseRenderer, TemplateRegistration


class ExtensionHost(Protocol):
    """扩展框架所需的宿主能力集合，由 ExtensionManager 实现。"""

    def register_extension(self, extension_id: str, extension: Extension) -> None:
        """登记一个已加载的扩展实例。"""
        ...

    def register_no_code_info(self, extension_id: str, info: dict[str, Any]) -> None:
        """登记一个无代码扩展包（template/resources）的展示信息。"""
        ...

    def register_service(self, name: str, service: object) -> None:
        """登记一个 API 服务。"""
        ...

    def get_service(self, name: str) -> object | None:
        """按名称获取已登记的服务。"""
        ...

    def register_renderer(self, renderer: BaseRenderer) -> None:
        """登记一个渲染引擎实例。"""
        ...

    def get_renderer(self, name: str) -> BaseRenderer | None:
        """按名称获取渲染引擎实例。"""
        ...

    def register_template(self, registration: TemplateRegistration) -> None:
        """登记一个 template 扩展包。"""
        ...

    def register_resources(self, extension_id: str, resources_dir: Path) -> None:
        """登记一个 resources 扩展包。"""
        ...

    def image_mode_enabled(self) -> bool:
        """当前是否启用图片输出模式（供 Loader/Command 判定分支，避免依赖 Core.Config）。"""
        ...
