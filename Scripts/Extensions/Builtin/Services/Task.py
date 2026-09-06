"""
内置服务：定时任务管理。

把 TaskManager 从 Scripts.Managers 抽取为内置 API 服务，供内置命令、事件处理器与
WebUI API 通过 `extension.api.get(TaskService)`（或全局注册名 `task`）获取。
服务直接代理全局 `task_manager` 单例，不复制调度状态，保证与 Bot 生命周期一致。
"""

from collections.abc import Callable, Coroutine
from typing import Any, override

from Scripts import Globals
from Scripts.Extensions import Extension, Service
from Scripts.Managers import task_manager
from Scripts.Messages import messages

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Task', name=messages.builtin_extensions.task, version='1.0.0', types=('api',))

TaskRunner = Callable[[], Coroutine[Any, Any, Any]]


@extension.register_service
class TaskService(Service):
    """封装定时任务管理能力，代理全局 `task_manager` 单例。"""

    name = 'task'

    @property
    def started(self) -> bool:
        """判断任务管理器是否已启动调度。"""
        return task_manager.started

    @property
    def task_names(self) -> list[str]:
        """返回全部已注册任务的名称。"""
        return task_manager.task_names

    def add(self, name: str, runner: TaskRunner, interval: float, *, immediate: bool = False) -> bool:
        """注册按固定间隔循环执行的任务，immediate 为 True 时先执行再等待。"""
        return task_manager.add(name, runner, interval, immediate=immediate)

    def add_once(self, name: str, runner: TaskRunner, delay: float) -> bool:
        """注册延迟指定秒数后仅执行一次的事务，执行完毕自动注销。"""
        return task_manager.add_once(name, runner, delay)

    def remove(self, name: str) -> bool:
        """注销并停止指定任务，未注册时返回 False。"""
        return task_manager.remove(name)

    def get(self, name: str) -> Any | None:
        """按名称获取任务对象。"""
        return task_manager.get(name)

    def status(self) -> dict[str, dict[str, Any]]:
        """输出全部任务的配置与运行状态快照，供调试与 WebUI 展示。"""
        return task_manager.status()

    def start_task(self, name: str) -> bool:
        """启动单个已注册任务的调度，已在运行时跳过。"""
        return task_manager.start_task(name)

    def stop_task(self, name: str) -> bool:
        """停止单个任务的调度，不影响其注册信息。"""
        return task_manager.stop_task(name)

    @override
    async def on_enable(self) -> None:
        """服务启动时确保任务管理器已开始调度。"""
        if not task_manager.started:
            await task_manager.start()
        Globals.task_service = self

    @override
    async def on_disable(self) -> None:
        """服务关闭时停止全部调度，保留注册信息以便重启恢复。"""
        if Globals.task_service is self:
            Globals.task_service = None
        if task_manager.started:
            await task_manager.stop()