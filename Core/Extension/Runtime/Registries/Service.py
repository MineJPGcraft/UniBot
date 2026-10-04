"""
服务注册表：全局 API 服务表 `name -> service` 的纯容器（含归属扩展）。

扩展经 `Extension.api`（即本容器）登记服务，供其它扩展与 WebUI 按注册名或
服务类查询；重名时以最新注册为准。服务实例的 `on_enable` / `on_disable`
生命周期编排由 `Managers/Service.py` 负责，本模块只登记与查询。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast, overload

from Core.Logging import logger

if TYPE_CHECKING:
    from ...Service import Service

ServiceT = TypeVar('ServiceT', bound='Service')


class ServiceRegistry:
    """全局 API 服务注册容器：name -> service（含归属扩展）。"""

    def __init__(self) -> None:
        self._services: dict[str, object] = {}
        # name -> 归属扩展 id（内置服务为对应扩展 id）
        self._owners: dict[str, str] = {}

    def clear(self) -> None:
        """清空全部注册项。"""
        self._services.clear()
        self._owners.clear()

    def register(self, name: str, service: object, *, owner_id: str = '') -> None:
        """注册一个 API 服务，重名时以最新注册为准。"""
        if name in self._services:
            logger.warning(f'API service {name} registered twice, the latest one wins.')
        self._services[name] = service
        self._owners[name] = owner_id

    def unregister(self, name: str) -> None:
        """注销一个 API 服务，不存在时静默忽略。"""
        self._services.pop(name, None)
        self._owners.pop(name, None)

    def unregister_by_owner(self, owner_id: str) -> list[str]:
        """注销某个扩展登记的全部服务，返回被移除的服务名列表。"""
        removed = [name for name, owner in self._owners.items() if owner == owner_id]
        for name in removed:
            self.unregister(name)
        return removed

    def owner_of(self, name: str) -> str:
        """获取服务的归属扩展 id（未登记返回空串）。"""
        return self._owners.get(name, '')

    @overload
    def get(self, name: str, /) -> object | None: ...

    @overload
    def get(self, service_type: type[ServiceT], /) -> ServiceT | None: ...

    def get(self, name: str | type[ServiceT], /) -> object | ServiceT | None:
        """按注册名或服务类获取 API 服务（未注册返回 None，类型不符抛 TypeError）。"""
        if isinstance(name, str):
            return self._services.get(name)
        key = name.name or name.__name__
        service = self._services.get(key)
        if service is None:
            return None
        if not isinstance(service, name):
            raise TypeError(f'API service {key} is not of type {name.__name__}!')
        return service

    def get_by_owner(self, owner_id: str) -> list[Service]:
        """返回某个扩展登记的服务实例（按登记顺序），供生命周期编排使用。"""
        return [cast('Service', service) for name, service in self._services.items() if self._owners.get(name) == owner_id]

    def all(self) -> dict[str, object]:
        """返回全部已注册服务的浅拷贝：name -> service。"""
        return dict(self._services)
