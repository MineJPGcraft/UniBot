"""
渲染引擎注册表：`name -> BaseRenderer` 的纯容器。

只保存已注册的渲染引擎实例；setup/并发/超时/关闭等编排由
`Managers/Renderer.py` 负责。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from Core.Logging import logger

if TYPE_CHECKING:
    from ...Renderer import BaseRenderer


class RendererRegistry:
    """已注册渲染引擎的注册容器：name -> BaseRenderer（含归属扩展）。"""

    def __init__(self) -> None:
        self._renderers: dict[str, BaseRenderer] = {}
        # name -> 归属扩展 id（用于按扩展回滚与注销）
        self._owners: dict[str, str] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self._renderers.clear()
        self._owners.clear()

    def register(self, renderer: BaseRenderer, *, owner_id: str = '') -> None:
        """注册一个渲染引擎实例（无名称的渲染器忽略，重名覆盖并告警）。"""
        if not renderer.name:
            return
        if renderer.name in self._renderers:
            logger.warning(f'Render engine {renderer.name} registered twice, the latest one wins.')
        self._renderers[renderer.name] = renderer
        self._owners[renderer.name] = owner_id

    def unregister(self, name: str) -> None:
        """按名称注销渲染引擎，不存在时静默忽略。"""
        self._renderers.pop(name, None)
        self._owners.pop(name, None)

    def unregister_by_owner(self, owner_id: str) -> list[str]:
        """注销某个扩展登记的全部渲染引擎，返回被移除的引擎名列表。"""
        removed = [name for name, owner in self._owners.items() if owner == owner_id]
        for name in removed:
            self.unregister(name)
        return removed

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
