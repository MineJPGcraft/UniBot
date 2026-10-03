"""
扩展/服务/渲染器注册表：集中存放注册状态并提供增删查。

从 `Manager.py` 抽出，使扩展管理器的生命周期编排与注册容器解耦：注册容器只
关心「有什么」，管理器只关心「何时加载/启停/渲染」。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from Core.Logging import logger

if TYPE_CHECKING:
    from ..Base import Extension
    from ..Renderer import BaseRenderer


class ExtensionRegistry:
    """扩展、服务、渲染器与无代码扩展包展示信息的统一注册容器。"""

    def __init__(self) -> None:
        self.extensions: dict[str, Extension] = {}
        self.services: dict[str, object] = {}
        self.renderers: dict[str, BaseRenderer] = {}
        # 无代码扩展包（template/resources）展示信息：extension_id -> info dict
        self.no_code_info: dict[str, dict] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self.extensions.clear()
        self.services.clear()
        self.renderers.clear()
        self.no_code_info.clear()

    # ===== 扩展 =====

    def register_extension(self, extension_id: str, extension: Extension) -> None:
        """登记一个已加载的扩展实例。"""
        self.extensions[extension_id] = extension

    def register_no_code_info(self, extension_id: str, info: dict) -> None:
        """登记一个无代码扩展包（template/resources）的展示信息。"""
        self.no_code_info[extension_id] = info

    # ===== 服务 =====

    def register_service(self, name: str, service: object) -> None:
        """注册一个 API 服务，重名时以最新注册为准。"""
        if name in self.services:
            logger.warning(f'API service {name} registered twice, the latest one wins.')
        self.services[name] = service

    def get_service(self, name: str) -> object | None:
        """获取已注册的 API 服务，未注册返回 None。"""
        return self.services.get(name)

    # ===== 渲染器 =====

    def register_renderer(self, renderer: BaseRenderer) -> None:
        """注册一个渲染引擎实例（无名称的渲染器忽略）。"""
        if renderer.name:
            self.renderers[renderer.name] = renderer

    def get_renderer(self, name: str) -> BaseRenderer | None:
        """获取指定名称的渲染引擎实例。"""
        return self.renderers.get(name)
