"""定时任务管理器：集中注册、调度、监控与停止所有周期性后台事务。

用法示例：
    task_manager.add('reporter-heartbeat', reporter.report, 300)
    await task_manager.start()
管理器启动后新注册的任务会立即进入调度，无需再次手动启动。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from Scripts.Logging import logger

# 允许注册的最小间隔（秒），防止空转过载事件循环
MIN_INTERVAL_SECONDS = 0.01

TaskRunner = Callable[[], Coroutine[Any, Any, Any]]


@dataclass
class ScheduledTask:
    """单个定时任务的配置与运行状态。"""

    name: str
    runner: TaskRunner
    interval: float
    immediate: bool = False
    once: bool = False
    task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def running(self) -> bool:
        """判断任务是否正在被调度运行。"""
        return self.task is not None and not self.task.done()


class TaskManager:
    """统一管理全部定时事务：支持周期循环任务与一次性延迟任务。"""

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._started = False

    @property
    def started(self) -> bool:
        """判断管理器是否已启动调度。"""
        return self._started

    @property
    def task_names(self) -> list[str]:
        """返回全部已注册任务的名称。"""
        return list(self._tasks)

    def add(self, name: str, runner: TaskRunner, interval: float, *, immediate: bool = False) -> bool:
        """注册按固定间隔循环执行的任务，immediate 为 True 时先执行再等待。"""
        return self._register(name, runner, interval, immediate=immediate)

    def add_once(self, name: str, runner: TaskRunner, delay: float) -> bool:
        """注册延迟指定秒数后仅执行一次的事务，执行完毕自动注销。"""
        return self._register(name, runner, delay, once=True)

    def remove(self, name: str) -> bool:
        """注销并停止指定任务，未注册时返回 False。"""
        task = self._tasks.pop(name, None)
        if task is None:
            return False
        self._cancel(task)
        logger.debug(f'Task {name} removed from task manager.')
        return True

    def get(self, name: str) -> ScheduledTask | None:
        """按名称获取任务对象。"""
        return self._tasks.get(name)

    def status(self) -> dict[str, dict[str, Any]]:
        """输出全部任务的配置与运行状态快照，供调试与 WebUI 展示。"""
        return {
            name: {
                'interval': task.interval,
                'immediate': task.immediate,
                'once': task.once,
                'running': task.running,
            }
            for name, task in self._tasks.items()
        }

    async def start(self) -> None:
        """启动管理器并为全部已注册任务建立调度，重复调用无副作用。"""
        if self._started:
            return
        self._started = True
        for name in self.task_names:
            self.start_task(name)
        logger.info(f'Task manager started with {len(self._tasks)} scheduled task(s).')

    async def stop(self) -> None:
        """停止全部调度并等待任务退出，保留注册信息以便重启恢复。"""
        if not self._started:
            return
        self._started = False
        running = [task.task for task in self._tasks.values() if task.running and task.task is not None]
        for task in self._tasks.values():
            self._cancel(task)
        if running:
            await asyncio.gather(*running, return_exceptions=True)
        logger.info(f'Task manager stopped with {len(running)} task(s) cancelled.')

    def start_task(self, name: str) -> bool:
        """启动单个已注册任务的调度，已在运行时跳过。"""
        task = self._tasks.get(name)
        if task is None or task.running:
            return False
        target = self._run_once(task) if task.once else self._run_periodic(task)
        task.task = asyncio.create_task(target, name=f'task-manager:{name}')
        logger.debug(f'Task {name} scheduling started.')
        return True

    def stop_task(self, name: str) -> bool:
        """停止单个任务的调度，不影响其注册信息。"""
        task = self._tasks.get(name)
        if task is None or not task.running:
            return False
        self._cancel(task)
        logger.debug(f'Task {name} scheduling stopped.')
        return True

    def _register(
        self, name: str, runner: TaskRunner, interval: float, *, immediate: bool = False, once: bool = False
    ) -> bool:
        if name in self._tasks:
            logger.warning(f'Task {name} is already registered, ignored.')
            return False
        if interval < MIN_INTERVAL_SECONDS:
            logger.warning(f'Task {name} rejected: interval {interval} is below the minimum.')
            return False
        self._tasks[name] = ScheduledTask(name=name, runner=runner, interval=interval, immediate=immediate, once=once)
        logger.debug(f'Task {name} registered (interval={interval}s, immediate={immediate}, once={once}).')
        if self._started:
            self.start_task(name)
        return True

    def _cancel(self, task: ScheduledTask) -> None:
        if task.task is None:
            return
        task.task.cancel()
        task.task = None

    async def _run_periodic(self, task: ScheduledTask) -> None:
        """按间隔循环执行任务体，单次失败只记录告警不中断后续调度。"""
        immediate = task.immediate
        while True:
            if not immediate:
                await asyncio.sleep(task.interval)
            immediate = False
            try:
                await task.runner()
            except Exception as error:
                logger.warning(f'Task {task.name} execution failed: {error}')

    async def _run_once(self, task: ScheduledTask) -> None:
        """延迟指定时间后执行一次任务体并自动注销。"""
        try:
            await asyncio.sleep(task.interval)
            await task.runner()
            logger.debug(f'Once task {task.name} finished.')
        except Exception as error:
            logger.warning(f'Once task {task.name} execution failed: {error}')
        finally:
            self._tasks.pop(task.name, None)


task_manager = TaskManager()
