"""
扩展注册表：已加载扩展实例与无代码扩展包展示信息的纯容器。

只保存「有什么」，生命周期编排由 `Runtime/Manager.py` 负责；
`api` 服务的全局表见 `Service.py`。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from Core.Logging import logger

if TYPE_CHECKING:
    from ...Extension import Extension


class ExtensionRegistry:
    """扩展实例与无代码扩展包展示信息的注册容器。"""

    def __init__(self) -> None:
        self.extensions: dict[str, Extension] = {}
        # 无代码扩展包（template/resources）展示信息：extension_id -> info dict
        self.no_code_info: dict[str, dict] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self.extensions.clear()
        self.no_code_info.clear()

    # ===== 扩展 =====

    def register_extension(self, extension_id: str, extension: Extension) -> None:
        """登记一个已加载的扩展实例（重复登记覆盖并告警）。"""
        if extension_id in self.extensions:
            logger.warning(f'Extension {extension_id} registered twice, the latest one wins.')
        self.extensions[extension_id] = extension

    def unregister_extension(self, extension_id: str) -> None:
        """注销一个扩展实例，不存在时静默忽略。"""
        self.extensions.pop(extension_id, None)

    def unregister_by_owner(self, extension_id: str) -> list[str]:
        """按归属扩展 id 注销其登记项（扩展实例 + 无代码包展示信息），返回被移除的 id 列表。

        与 `ServiceRegistry` / `CommandRegistry` / 渲染器注册表的 `unregister_by_owner`
        保持对称；本容器中扩展实例与无代码包展示信息均以扩展 id 为键，故二者一并清理。
        """
        removed = [extension_id] if extension_id in self.extensions else []
        self.extensions.pop(extension_id, None)
        if self.no_code_info.pop(extension_id, None) is not None:
            removed.append(extension_id)
        return removed

    def get_extension(self, extension_id: str) -> Extension | None:
        """按 id 获取扩展实例，未登记返回 None。"""
        return self.extensions.get(extension_id)

    # ===== 无代码扩展包展示信息 =====

    def register_no_code_info(self, extension_id: str, info: dict) -> None:
        """登记一个无代码扩展包（template/resources）的展示信息。"""
        self.no_code_info[extension_id] = info

    def unregister_no_code_info(self, extension_id: str) -> None:
        """注销无代码扩展包的展示信息。"""
        self.no_code_info.pop(extension_id, None)
