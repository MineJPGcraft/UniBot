"""
API 服务基类与受限服务注册入口。

扩展通过继承 `Service` 定义可被其它扩展或内置代码复用的服务能力，
由 `@extension.register_service` 装饰器标记，Loader 统一实例化并提交到全局注册表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, overload

from Scripts.Logging import logger

if TYPE_CHECKING:
    from .Manager import ExtensionManager


ServiceT = TypeVar('ServiceT', bound='Service')


class Service:
    """API 服务基类，扩展能力服务应继承此类。"""

    # 服务注册名（缺省使用类名），供其它扩展通过 self.api.get(name) 获取
    name: str = ''

    # ===== 生命周期 =====

    async def on_enable(self) -> None:
        """服务启动时调用（可选覆盖），用于初始化外部资源。"""

    async def on_disable(self) -> None:
        """服务关闭时调用（可选覆盖），用于释放外部资源。"""


class ServiceRegistry:
    """扩展的服务注册入口，将服务写入全局 ExtensionManager。"""

    def __init__(self, manager: ExtensionManager) -> None:
        self._manager = manager
        self._services: list[Service] = []

    def register(self, name: str, service: Service) -> None:
        """注册一个 API 服务，供其它扩展或内置代码获取。"""
        self._manager.register_service(name, service)
        self._services.append(service)

    async def enable(self) -> None:
        """按注册顺序启动当前扩展的服务。"""
        enabled_services: list[Service] = []
        try:
            for service in self._services:
                await service.on_enable()
                enabled_services.append(service)
        except Exception:
            await self._disable_services(enabled_services)
            raise

    async def disable(self) -> None:
        """按注册逆序关闭当前扩展的服务。"""
        await self._disable_services(self._services)

    @staticmethod
    async def _disable_services(services: list[Service]) -> None:
        """关闭指定服务，单个服务失败不阻止其余服务清理。"""
        for service in reversed(services):
            try:
                await service.on_disable()
            except Exception as error:
                name = service.name or type(service).__name__
                logger.error(f'API service {name} failed to shut down: {error}')

    @overload
    def get(self, service_type: type[ServiceT], /) -> ServiceT | None: ...

    @overload
    def get(self, service_type: str, /) -> object | None: ...

    def get(self, service_type: str | type[ServiceT], /) -> object | ServiceT | None:
        """按服务类或注册名获取 API 服务（未注册返回 None）。"""
        if isinstance(service_type, str):
            return self._manager.get_service(service_type)
        name = service_type.name or service_type.__name__
        service = self._manager.get_service(name)
        if service is None:
            return None
        if not isinstance(service, service_type):
            raise TypeError(f'API service {name} is not of type {service_type.__name__}!')
        return service
