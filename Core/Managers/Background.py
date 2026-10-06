"""后台事务调度器：集中注册、调度、监控与停止所有周期性后台事务。

与任务中心（`Core.Managers.TaskCenter`）职责不同：本模块只负责**周期性/延迟调度**，
任务中心负责**一次性长耗时业务**的提交、进度与取消。

用法示例：
    background_manager.add('reporter-heartbeat', reporter.report, 300)
    await background_manager.start()
调度器启动后新注册的事务会立即进入调度，无需再次手动启动。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from Core.Logging import logger

# 允许注册的最小间隔（秒），防止空转过载事件循环
MIN_INTERVAL_SECONDS = 0.01

BackgroundRunner = Callable[[], Coroutine[Any, Any, Any]]


@dataclass
class BackgroundJob:
    """单个后台事务的配置与运行状态。"""

    name: str
    runner: BackgroundRunner
    interval: float
    immediate: bool = False
    once: bool = False
    task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def running(self) -> bool:
        """判断事务是否正在被调度运行。"""
        return self.task is not None and not self.task.done()


class BackgroundManager:
    """统一管理全部后台事务：支持周期循环事务与一次性延迟事务。"""

    def __init__(self) -> None:
        self._jobs: dict[str, BackgroundJob] = {}
        self._started = False

    @property
    def started(self) -> bool:
        """判断调度器是否已启动。"""
        return self._started

    @property
    def job_names(self) -> list[str]:
        """返回全部已注册事务的名称。"""
        return list(self._jobs)

    def add(self, name: str, runner: BackgroundRunner, interval: float, *, immediate: bool = False) -> bool:
        """注册按固定间隔循环执行的事务，immediate 为 True 时先执行再等待。"""
        return self._register(name, runner, interval, immediate=immediate)

    def add_once(self, name: str, runner: BackgroundRunner, delay: float) -> bool:
        """注册延迟指定秒数后仅执行一次的事务，执行完毕自动注销。"""
        return self._register(name, runner, delay, once=True)

    def remove(self, name: str) -> bool:
        """注销并停止指定事务，未注册时返回 False。"""
        job = self._jobs.pop(name, None)
        if job is None:
            return False
        self._cancel(job)
        logger.debug(f'Background job {name} removed from background manager.')
        return True

    def get(self, name: str) -> BackgroundJob | None:
        """按名称获取事务对象。"""
        return self._jobs.get(name)

    def status(self) -> dict[str, dict[str, Any]]:
        """输出全部事务的配置与运行状态快照，供调试与 WebUI 展示。"""
        return {
            name: {
                'interval': job.interval,
                'immediate': job.immediate,
                'once': job.once,
                'running': job.running,
            }
            for name, job in self._jobs.items()
        }

    async def start(self) -> None:
        """启动调度器并为全部已注册事务建立调度，重复调用无副作用。"""
        if self._started:
            return
        self._started = True
        for name in self.job_names:
            self.start_job(name)
        logger.info(f'Background manager started with {len(self._jobs)} scheduled job(s).')

    async def stop(self) -> None:
        """停止全部调度并等待事务退出，保留注册信息以便重启恢复。"""
        if not self._started:
            return
        self._started = False
        running = [job.task for job in self._jobs.values() if job.running and job.task is not None]
        for job in self._jobs.values():
            self._cancel(job)
        if running:
            await asyncio.gather(*running, return_exceptions=True)
        logger.info(f'Background manager stopped with {len(running)} job(s) cancelled.')

    def start_job(self, name: str) -> bool:
        """启动单个已注册事务的调度，已在运行时跳过。"""
        job = self._jobs.get(name)
        if job is None or job.running:
            return False
        target = self._run_once(job) if job.once else self._run_periodic(job)
        job.task = asyncio.create_task(target, name=f'background-manager:{name}')
        logger.debug(f'Background job {name} scheduling started.')
        return True

    def stop_job(self, name: str) -> bool:
        """停止单个事务的调度，不影响其注册信息。"""
        job = self._jobs.get(name)
        if job is None or not job.running:
            return False
        self._cancel(job)
        logger.debug(f'Background job {name} scheduling stopped.')
        return True

    def _register(
        self, name: str, runner: BackgroundRunner, interval: float, *, immediate: bool = False, once: bool = False
    ) -> bool:
        if name in self._jobs:
            logger.warning(f'Background job {name} is already registered, ignored.')
            return False
        if interval < MIN_INTERVAL_SECONDS:
            logger.warning(f'Background job {name} rejected: interval {interval} is below the minimum.')
            return False
        self._jobs[name] = BackgroundJob(name=name, runner=runner, interval=interval, immediate=immediate, once=once)
        logger.debug(f'Background job {name} registered (interval={interval}s, immediate={immediate}, once={once}).')
        if self._started:
            self.start_job(name)
        return True

    def _cancel(self, job: BackgroundJob) -> None:
        if job.task is None:
            return
        job.task.cancel()
        job.task = None

    async def _run_periodic(self, job: BackgroundJob) -> None:
        """按间隔循环执行事务体，单次失败只记录告警不中断后续调度。"""
        immediate = job.immediate
        while True:
            if not immediate:
                await asyncio.sleep(job.interval)
            immediate = False
            try:
                await job.runner()
            except Exception as error:
                logger.warning(f'Background job {job.name} execution failed: {error}')

    async def _run_once(self, job: BackgroundJob) -> None:
        """延迟指定时间后执行一次事务体并自动注销。"""
        try:
            await asyncio.sleep(job.interval)
            await job.runner()
            logger.debug(f'Once background job {job.name} finished.')
        except Exception as error:
            logger.warning(f'Once background job {job.name} execution failed: {error}')
        finally:
            self._jobs.pop(job.name, None)


background_manager = BackgroundManager()
