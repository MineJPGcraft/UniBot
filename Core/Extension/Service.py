"""
API 服务基类。

扩展通过继承 `Service` 定义可被其它扩展或内置代码复用的服务能力，
由 `@extension.register_service` 装饰器标记，Loader 统一实例化并提交到全局服务容器
（`Runtime/Registries/Service.py`）；启停编排位于 `Runtime/Managers/Service.py`
（扩展作者无需接触）。
"""

from __future__ import annotations


class Service:
    """API 服务基类，扩展能力服务应继承此类。"""

    # 服务注册名（缺省使用类名），供其它扩展通过 self.api.get(name) 获取
    name: str = ''

    # ===== 生命周期 =====

    async def on_enable(self) -> None:
        """服务启动时调用（可选覆盖），用于初始化外部资源。"""

    async def on_disable(self) -> None:
        """服务关闭时调用（可选覆盖），用于释放外部资源。"""
