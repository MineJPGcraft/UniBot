"""
模板包注册表：`extension_id -> TemplateRegistration` 的纯容器。

只保存已注册的 template 无代码扩展包；Jinja2 环境构建、渲染协商与缓存
失效由 `Managers/Renderer.py` 负责。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from Core.Logging import logger

if TYPE_CHECKING:
    from ...Renderer import TemplateRegistration


class TemplateRegistry:
    """已注册模板包的注册容器：extension_id -> TemplateRegistration。"""

    def __init__(self) -> None:
        self._templates: dict[str, TemplateRegistration] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self._templates.clear()

    def register(self, registration: TemplateRegistration) -> None:
        """注册一个 template 扩展包（重复注册覆盖并告警）。"""
        if registration.extension_id in self._templates:
            logger.warning(f'Template extension {registration.extension_id} registered twice, the latest one wins.')
        self._templates[registration.extension_id] = registration

    def unregister(self, extension_id: str) -> None:
        """注销模板扩展包，不存在时静默忽略。"""
        self._templates.pop(extension_id, None)

    def get(self, extension_id: str) -> TemplateRegistration | None:
        """按扩展 id 获取模板注册信息，未注册返回 None。"""
        return self._templates.get(extension_id)

    def all(self) -> dict[str, TemplateRegistration]:
        """返回全部已注册模板注册信息的浅拷贝。"""
        return dict(self._templates)

    def __contains__(self, extension_id: str) -> bool:
        return extension_id in self._templates
