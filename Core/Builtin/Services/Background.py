"""
内置服务：后台事务调度。

把 BackgroundManager 从 Core.Managers 抽取为内置 API 服务，供内置命令、事件处理器与
WebUI API 通过 `extension.api.get(BackgroundService)`（或全局注册名 `background`）获取。
服务直接代理全局 `background_manager` 单例，不复制调度状态，保证与 Bot 生命周期一致。
"""

from collections.abc import Callable, Coroutine
from typing import Any, override

from Core.Extension import Extension, Service
from Core.I18n import i18n_deferred
from Core.Managers import background_manager
from Core.RuntimeState import runtime_state

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Background', name=i18n_deferred('builtin.background.name'), version='1.0.0', types=('api',))

BackgroundRunner = Callable[[], Coroutine[Any, Any, Any]]


@extension.register_service
class BackgroundService(Service):
    """封装后台事务调度能力，代理全局 `background_manager` 单例。"""

    name = 'background'

    @property
    def started(self) -> bool:
        """判断调度器是否已启动。"""
        return background_manager.started

    @property
    def job_names(self) -> list[str]:
        """返回全部已注册事务的名称。"""
        return background_manager.job_names

    def add(self, name: str, runner: BackgroundRunner, interval: float, *, immediate: bool = False) -> bool:
        """注册按固定间隔循环执行的事务，immediate 为 True 时先执行再等待。"""
        return background_manager.add(name, runner, interval, immediate=immediate)

    def add_once(self, name: str, runner: BackgroundRunner, delay: float) -> bool:
        """注册延迟指定秒数后仅执行一次的事务，执行完毕自动注销。"""
        return background_manager.add_once(name, runner, delay)

    def remove(self, name: str) -> bool:
        """注销并停止指定事务，未注册时返回 False。"""
        return background_manager.remove(name)

    def get(self, name: str) -> Any | None:
        """按名称获取事务对象。"""
        return background_manager.get(name)

    def status(self) -> dict[str, dict[str, Any]]:
        """输出全部事务的配置与运行状态快照，供调试与 WebUI 展示。"""
        return background_manager.status()

    def start_job(self, name: str) -> bool:
        """启动单个已注册事务的调度，已在运行时跳过。"""
        return background_manager.start_job(name)

    def stop_job(self, name: str) -> bool:
        """停止单个事务的调度，不影响其注册信息。"""
        return background_manager.stop_job(name)

    @override
    async def on_enable(self) -> None:
        """服务启动时确保调度器已开始调度。"""
        if not background_manager.started:
            await background_manager.start()
        runtime_state.background_service = self

    @override
    async def on_disable(self) -> None:
        """服务关闭时停止全部调度，保留注册信息以便重启恢复。"""
        if runtime_state.background_service is self:
            runtime_state.background_service = None
        if background_manager.started:
            await background_manager.stop()
