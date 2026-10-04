"""
服务生命周期管理器：编排 API 服务实例的启停。

服务登记（`name -> service`，含归属扩展）写在全局 `ServiceRegistry` 容器中；
本管理器只负责按扩展（`owner_id`）取出其服务并调用 `on_enable` / `on_disable`，
并在启动失败时回滚已启用服务。
"""

from __future__ import annotations

from Core.Logging import logger

from ...Service import Service
from ..Registries import ServiceRegistry


class ServiceManager:
    """编排 API 服务实例的启用与停用。"""

    def __init__(self, registry: ServiceRegistry | None = None) -> None:
        # 全局服务容器由 ExtensionManager 创建后按引用传入；独立使用（测试）时自建
        self._registry = registry if registry is not None else ServiceRegistry()

    @property
    def registry(self) -> ServiceRegistry:
        """全局服务注册容器：name -> service。"""
        return self._registry

    def get(self, name: str) -> object | None:
        """按注册名获取服务，未注册返回 None。"""
        return self._registry.get(name)

    async def enable(self, owner_id: str) -> None:
        """按登记顺序启动某扩展的全部服务；中途失败时回滚已启动部分。"""
        enabled_services: list[Service] = []
        try:
            for service in self._registry.get_by_owner(owner_id):
                await service.on_enable()
                enabled_services.append(service)
        except Exception:
            await self._disable_services(enabled_services)
            raise

    async def disable(self, owner_id: str) -> None:
        """按登记逆序关闭某扩展的全部服务。"""
        await self._disable_services(self._registry.get_by_owner(owner_id))

    @staticmethod
    async def _disable_services(services: list[Service]) -> None:
        """关闭指定服务，单个服务失败不阻止其余服务清理。"""
        for service in reversed(services):
            try:
                await service.on_disable()
            except Exception as error:
                name = service.name or type(service).__name__
                logger.error(f'API service {name} failed to shut down: {error}')
