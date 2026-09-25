"""后台任务中心：统一登记、执行与追踪耗时操作（依赖安装、扩展市场、热重载等）。

WebUI 右上角「任务中心」读取本模块的状态快照。设计要点：

- 任务体是异步函数，接收 `TaskContext`，通过 `log` / `set_message` / `set_progress`
  回报进度；返回值为成功消息键（成功即 succeeded，抛异常即 failed）。
- 任务标题与进度消息一律以「消息键 + 参数」下发，由前端按界面语言翻译，
  保证任务在任意语言请求下触发都能正确本地化；日志与错误原文是数据，不做翻译。
- 状态变更通过 WebSocket 的 `task` 事件广播给订阅客户端（无事件循环时静默跳过）。
- 历史仅保存在内存中（保留最近 MAX_HISTORY 条），重启后清空。
"""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from Scripts.Constants import TaskKind
from Scripts.Logging import exception_logger, logger

# 保留的历史任务上限（超出后丢弃最旧的非运行中任务）
MAX_HISTORY = 50
# 单个任务保留的日志行数上限
MAX_LOG_LINES = 300


class TaskStatus(StrEnum):
    """后台任务生命周期状态。成员值即下发给 WebUI 的状态码。"""

    pending = 'pending'
    running = 'running'
    succeeded = 'succeeded'
    failed = 'failed'
    cancelled = 'cancelled'


# 未结束的状态（不允许被历史淘汰）
ACTIVE_STATUSES = (TaskStatus.pending, TaskStatus.running)


class TaskCancelledError(Exception):
    """任务被用户取消时抛出（区别于普通失败）。"""


@dataclass
class TaskRecord:
    """单个后台任务的配置与运行状态。"""

    id: str
    kind: TaskKind
    title_params: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.pending
    message_key: str = ''
    message_params: dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    error: str = ''
    logs: list[str] = field(default_factory=list)
    # 任务产出（如 Studio 启动后的访问地址），供前端读取
    result: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0
    retryable: bool = False
    # 运行句柄与重试工厂仅内存持有，不对外序列化
    handle: asyncio.Task | None = field(default=None, repr=False)
    # create_task 需要协程对象，故工厂声明为协程而非更宽的 Awaitable
    factory: Callable[[], Coroutine[Any, Any, str | None]] | None = field(default=None, repr=False)

    @property
    def active(self) -> bool:
        """判断任务是否仍在排队或运行中。"""
        return self.status in ACTIVE_STATUSES

    def snapshot(self, *, with_logs: bool = False) -> dict[str, Any]:
        """输出任务状态快照（供 REST 与 WebSocket 使用）。"""
        data = {
            'id': self.id,
            'kind': self.kind,
            'title_params': self.title_params,
            'status': self.status,
            'message_key': self.message_key,
            'message_params': self.message_params,
            'progress': round(self.progress, 1),
            'error': self.error,
            'result': dict(self.result),
            'created_at': self.created_at,
            'started_at': self.started_at,
            'finished_at': self.finished_at,
            'retryable': self.retryable and not self.active,
            'log_count': len(self.logs),
        }
        if with_logs:
            data['logs'] = list(self.logs)
        return data


class TaskContext:
    """任务执行上下文：向任务体暴露日志与进度回报入口。"""

    def __init__(self, center: TaskCenter, record: TaskRecord) -> None:
        self._center = center
        self._record = record

    @property
    def cancelled(self) -> bool:
        """判断任务是否已被请求取消，任务体应在长流程中主动检查。"""
        return self._record.status == TaskStatus.cancelled

    def log(self, message: str) -> None:
        """追加一行任务日志并广播（超出上限时丢弃最旧行）。"""
        self._record.logs.append(message)
        if len(self._record.logs) > MAX_LOG_LINES:
            del self._record.logs[0]
        self._center.notify(self._record)

    def set_message(self, message_key: str, **params: Any) -> None:
        """更新当前阶段说明（消息键由前端翻译）。"""
        self._record.message_key = message_key
        self._record.message_params = params
        self._center.notify(self._record)

    def set_progress(self, progress: float) -> None:
        """更新进度百分比（0-100）。"""
        self._record.progress = max(0.0, min(100.0, progress))
        self._center.notify(self._record)

    def set_result(self, **result: Any) -> None:
        """记录任务产出（如启动成功的访问地址），供前端在任务完成后读取。"""
        self._record.result = result
        self._center.notify(self._record)

    def raise_if_cancelled(self) -> None:
        """已请求取消时中断任务。"""
        if self.cancelled:
            raise TaskCancelledError('Task cancelled by user.')


TaskRunner = Callable[[TaskContext], Awaitable[str | None] | str | None]


async def resolve_runner_result(result: Awaitable[str | None] | str | None) -> str | None:
    """兼容同步与异步任务体：协程 / awaitable 会被等待，其它值直接透传。"""
    if inspect.isawaitable(result):
        return await result
    return result


class TaskCenter:
    """后台任务中心单例：提交、查询、取消与重试。"""

    def __init__(self) -> None:
        self._records: dict[str, TaskRecord] = {}
        self._order: list[str] = []

    # ===== 查询 =====

    def list_tasks(self) -> list[dict[str, Any]]:
        """按创建时间倒序列出全部任务快照。"""
        return [self._records[task_id].snapshot() for task_id in reversed(self._order)]

    def get(self, task_id: str) -> TaskRecord | None:
        """按 id 获取任务记录。"""
        return self._records.get(task_id)

    def summary(self) -> dict[str, int]:
        """统计各状态任务数量，供任务中心角标展示。键为状态字符串（JSON 契约）。"""
        counts: dict[str, int] = {status.value: 0 for status in ACTIVE_STATUSES}
        for record in self._records.values():
            if record.status in ACTIVE_STATUSES:
                counts[record.status] += 1
        return counts

    # ===== 提交与执行 =====

    def submit(
        self,
        kind: TaskKind,
        runner: TaskRunner,
        *,
        title_params: dict[str, Any] | None = None,
        retryable: bool = True,
        message_key: str = 'task_center.msg_queued',
    ) -> dict[str, Any]:
        """登记并启动一个后台任务，立即返回任务快照。"""
        record = TaskRecord(
            id=uuid.uuid4().hex[:12],
            kind=kind,
            title_params=title_params or {},
            message_key=message_key,
            retryable=retryable,
        )
        record.factory = lambda: self._execute(record, runner)
        self._records[record.id] = record
        self._order.append(record.id)
        self._prune()
        record.handle = asyncio.create_task(record.factory(), name=f'task-center:{kind}')
        logger.debug(f'Task {record.id} ({kind}) submitted.')
        return record.snapshot()

    async def _execute(self, record: TaskRecord, runner: TaskRunner) -> str | None:
        """执行任务体并维护状态机（成功消息键 / 失败原因 / 取消）。"""
        record.status = TaskStatus.running
        record.started_at = time.time()
        record.message_key = 'task_center.msg_running'
        self.notify(record)
        try:
            message_key = await resolve_runner_result(runner(TaskContext(self, record)))
        except asyncio.CancelledError:
            self._finish(record, TaskStatus.cancelled, 'task_center.msg_cancelled')
            logger.info(f'Task {record.id} ({record.kind}) cancelled.')
            return None
        except TaskCancelledError:
            self._finish(record, TaskStatus.cancelled, 'task_center.msg_cancelled')
            return None
        except Exception as error:
            self._finish(record, TaskStatus.failed, 'task_center.msg_failed', error=str(error))
            exception_logger.error(f'Task {record.id} ({record.kind}) failed: {error}')
            return None
        self._finish(record, TaskStatus.succeeded, message_key or 'task_center.msg_finished', progress=100.0)
        logger.success(f'Task {record.id} ({record.kind}) finished.')
        return None

    def _finish(
        self,
        record: TaskRecord,
        status: TaskStatus,
        message_key: str,
        *,
        error: str = '',
        progress: float | None = None,
    ) -> None:
        """落定任务终态：写状态/时间戳 → 广播 → 淘汰超额历史。"""
        record.status = status
        record.message_key = message_key
        if error:
            record.error = error
        if progress is not None:
            record.progress = progress
        record.finished_at = time.time()
        self.notify(record)
        self._prune()

    # ===== 取消与重试 =====
    def cancel(self, task_id: str) -> tuple[bool, str]:
        """请求取消指定任务，返回 (是否受理, 消息键)。"""
        record = self._records.get(task_id)
        if record is None:
            return False, 'task_center.not_found'
        if not record.active:
            return False, 'task_center.not_cancellable'
        if record.handle is not None:
            record.handle.cancel()
        self._finish(record, TaskStatus.cancelled, 'task_center.msg_cancelled')
        return True, 'task_center.cancelled'

    def retry(self, task_id: str) -> tuple[bool, str]:
        """以同一任务体重新提交一个任务（原任务必须已结束且可重试）。"""
        record = self._records.get(task_id)
        if record is None:
            return False, 'task_center.not_found'
        if record.active:
            return False, 'task_center.not_retryable'
        if not record.retryable or record.factory is None:
            return False, 'task_center.not_retryable'
        record.status = TaskStatus.pending
        record.progress = 0.0
        record.error = ''
        record.result = {}
        record.logs = []
        record.created_at = time.time()
        record.started_at = 0.0
        record.finished_at = 0.0
        record.message_key = 'task_center.msg_queued'
        record.handle = asyncio.create_task(record.factory(), name=f'task-center:{record.kind}')
        self.notify(record)
        return True, 'task_center.retried'

    # ===== 内部工具 =====

    def _prune(self) -> None:
        """超出历史上限时淘汰最旧的已结束任务。"""
        while len(self._order) > MAX_HISTORY:
            for index, task_id in enumerate(self._order):
                if not self._records[task_id].active:
                    self._records.pop(task_id, None)
                    del self._order[index]
                    break
            else:
                return

    def notify(self, record: TaskRecord) -> None:
        """向 WebSocket 客户端广播任务状态（无运行中事件循环时静默跳过）。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        # 函数内导入：Scripts.Api 聚合全部路由，顶层导入会拖入插件托管包
        from Scripts.Api.WebSocket import broadcast_event

        loop.create_task(broadcast_event('task', record.snapshot()))


task_center = TaskCenter()
