"""
资源包注册表：`extension_id -> 资源根目录` 的纯容器。

只保存已注册的 resources 无代码扩展包根目录；路径解析与渲染期读取由
`Managers/Renderer.py` 负责。
"""

from __future__ import annotations

from pathlib import Path


class ResourcesRegistry:
    """已注册资源包的注册容器：extension_id -> 资源根目录。"""

    def __init__(self) -> None:
        self._roots: dict[str, Path] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self._roots.clear()

    def register(self, extension_id: str, resources_dir: Path) -> None:
        """注册一个 resources 扩展包根目录。"""
        self._roots[extension_id] = resources_dir

    def unregister(self, extension_id: str) -> None:
        """注销 resources 扩展包，不存在时静默忽略。"""
        self._roots.pop(extension_id, None)

    def get(self, extension_id: str) -> Path | None:
        """按扩展 id 获取资源根目录，未注册返回 None。"""
        return self._roots.get(extension_id)

    def all(self) -> dict[str, Path]:
        """返回全部已注册资源根目录的浅拷贝。"""
        return dict(self._roots)

    def __contains__(self, extension_id: str) -> bool:
        return extension_id in self._roots
