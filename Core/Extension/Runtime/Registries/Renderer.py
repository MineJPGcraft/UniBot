"""
渲染引擎注册表：`name -> BaseRenderer` 的纯容器。

只保存已注册的渲染引擎实例；setup/并发/超时/关闭等编排由
`Managers/Renderer.py` 负责。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...Renderer import BaseRenderer


class RendererRegistry:
    """已注册渲染引擎的注册容器：name -> BaseRenderer。"""

    def __init__(self) -> None:
        self._renderers: dict[str, BaseRenderer] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self._renderers.clear()

    def register(self, renderer: BaseRenderer) -> None:
        """注册一个渲染引擎实例（无名称的渲染器忽略）。"""
        if renderer.name:
            self._renderers[renderer.name] = renderer

    def unregister(self, name: str) -> None:
        """按名称注销渲染引擎，不存在时静默忽略。"""
        self._renderers.pop(name, None)

    def get(self, name: str) -> BaseRenderer | None:
        """按名称获取渲染引擎，未注册返回 None。"""
        return self._renderers.get(name)

    def resolve_name(self, name: str) -> str | None:
        """按注册名解析引擎名：完全匹配优先，其次大小写不敏感匹配。"""
        if name in self._renderers:
            return name
        lowered = name.lower()
        for candidate in self._renderers:
            if candidate.lower() == lowered:
                return candidate
        return None

    def all(self) -> dict[str, BaseRenderer]:
        """返回全部已注册引擎，未注册时为空字典。"""
        return self._renderers
