"""
任务中心测试。

验证方案：直接驱动 TaskCenter 的提交/执行/取消/重试/摘要/淘汰逻辑。
任务体为可控的异步桩函数，不触发任何真实 uv / 网络操作。
本仓库测试统一使用 `asyncio.run` 包裹异步场景（未引入 pytest-asyncio）。
"""

import asyncio

from Scripts.Managers.TaskCenter import (
    MAX_HISTORY,
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    TaskCancelledError,
    TaskCenter,
)


def _runner_success(context) -> str:
    """同步成功的任务体（任务中心允许同步返回）。"""
    context.log('work done')
    return 'task_center.msg_finished'


async def _runner_async_success(context) -> str:
    """异步成功的任务体。"""
    context.set_message('task_center.msg_running')
    context.log('async work done')
    return 'task_center.msg_finished'


async def _runner_failure(context) -> str:
    """抛异常的任务体。"""
    raise RuntimeError('boom')


async def _runner_cancellable(context) -> str:
    """等待取消信号的任务体。"""
    for _ in range(300):
        context.raise_if_cancelled()
        await asyncio.sleep(0.01)
    return 'task_center.msg_finished'


# ===== 提交与执行 =====


class TestSubmitAndExecute:
    def test_submit_returns_pending_snapshot(self):
        """提交后立即返回含标题参数的快照。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_async_success, title_params={'name': 'ExtA'})
            assert snapshot['status'] in ('pending', 'running')
            assert snapshot['title_params'] == {'name': 'ExtA'}
            assert snapshot['kind'] == 'demo'
            await asyncio.sleep(0.05)

        asyncio.run(run())

    def test_successful_task_records_result(self):
        """任务成功时状态为 succeeded，并保留最终消息键。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_async_success)
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.status == STATUS_SUCCEEDED
            assert record.message_key == 'task_center.msg_finished'
            assert record.error == ''
            assert record.progress == 100.0

        asyncio.run(run())

    def test_sync_runner_is_supported(self):
        """同步任务体会被 create_task 包装执行。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_success)
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.status == STATUS_SUCCEEDED

        asyncio.run(run())

    def test_failed_task_records_error(self):
        """任务失败时状态为 failed 且记录错误原文。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_failure)
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.status == STATUS_FAILED
            assert 'boom' in record.error
            assert record.message_key == 'task_center.msg_failed'

        asyncio.run(run())


# ===== 取消与重试 =====


class TestCancelAndRetry:
    def test_cancel_running_task(self):
        """运行中的任务可被取消，状态转为 cancelled 并返回受理。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_cancellable)
            await asyncio.sleep(0.05)

            success, message = center.cancel(snapshot['id'])
            assert success is True
            assert message == 'task_center.cancelled'
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.status == STATUS_CANCELLED

        asyncio.run(run())

    def test_cancel_finished_task_is_rejected(self):
        """已结束的任务不可取消。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_async_success)
            await asyncio.sleep(0.05)

            success, message = center.cancel(snapshot['id'])
            assert success is False
            assert message == 'task_center.not_cancellable'

        asyncio.run(run())

    def test_cancel_unknown_task(self):
        """取消不存在的任务返回 not_found 文案键。"""
        center = TaskCenter()
        success, message = center.cancel('missing')
        assert success is False
        assert message == 'task_center.not_found'

    def test_retry_resubmits_failed_task(self):
        """可重试的失败任务能重新提交并再次执行。"""
        calls = {'count': 0}

        async def flaky(context) -> str:
            calls['count'] += 1
            if calls['count'] == 1:
                raise RuntimeError('first attempt fails')
            return 'task_center.msg_finished'

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', flaky)
            await asyncio.sleep(0.05)
            assert center.get(snapshot['id']).status == STATUS_FAILED

            success, message = center.retry(snapshot['id'])
            assert success is True
            assert message == 'task_center.retried'
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.status == STATUS_SUCCEEDED
            assert calls['count'] == 2

        asyncio.run(run())

    def test_non_retryable_task_is_rejected(self):
        """retryable=False 的任务不可重试。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_failure, retryable=False)
            await asyncio.sleep(0.05)

            success, message = center.retry(snapshot['id'])
            assert success is False
            assert message == 'task_center.not_retryable'

        asyncio.run(run())


# ===== 摘要与历史 =====


class TestSummaryAndHistory:
    def test_summary_counts_active_tasks(self):
        """摘要统计活跃任务数量（pending + running）。"""

        async def run():
            center = TaskCenter()
            center.submit('demo', _runner_cancellable)
            await asyncio.sleep(0.02)

            summary = center.summary()
            assert summary['pending'] + summary['running'] == 1
            center.cancel(center.list_tasks()[0]['id'])
            await asyncio.sleep(0.05)
            assert sum(center.summary().values()) == 0

        asyncio.run(run())

    def test_history_is_pruned(self):
        """历史数量超过上限时淘汰最旧的已结束任务。"""

        async def run():
            center = TaskCenter()
            created = [center.submit('demo', _runner_success)['id'] for _ in range(MAX_HISTORY + 5)]
            await asyncio.sleep(0.3)

            items = center.list_tasks()
            assert len(items) <= MAX_HISTORY
            assert created[-1] in {item['id'] for item in items}

        asyncio.run(run())

    def test_list_tasks_newest_first(self):
        """任务列表按创建时间倒序排列。"""

        async def run():
            center = TaskCenter()
            first = center.submit('demo', _runner_success)['id']
            second = center.submit('demo', _runner_success)['id']
            await asyncio.sleep(0.05)

            ids = [item['id'] for item in center.list_tasks()]
            assert ids.index(second) < ids.index(first)

        asyncio.run(run())

    def test_snapshot_excludes_logs_by_default(self):
        """默认快照不含日志正文，只带条数（避免列表接口体积过大）。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_success)
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            final = record.snapshot()
            assert 'logs' not in final
            assert final['log_count'] == 1
            assert 'logs' in record.snapshot(with_logs=True)

        asyncio.run(run())


# ===== 任务上下文 =====


class TestTaskContext:
    def test_context_helpers(self):
        """上下文提供日志、消息、进度与结果改写能力。"""

        async def run():
            center = TaskCenter()

            async def runner(context) -> str:
                context.set_message('task_center.msg_running', name='ExtA')
                context.set_progress(42.5)
                context.set_result(url='http://127.0.0.1:3000')
                context.log('hello')
                return 'task_center.msg_finished'

            snapshot = center.submit('demo', runner)
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.message_params == {'name': 'ExtA'}
            assert record.result == {'url': 'http://127.0.0.1:3000'}
            # 任务成功后进度收敛到 100，日志保留原文
            assert record.progress == 100.0
            assert record.logs == ['hello']

        asyncio.run(run())

    def test_cancelled_task_status(self):
        """取消后 raise_if_cancelled 生效，任务以 cancelled 结束。"""

        async def run():
            center = TaskCenter()
            snapshot = center.submit('demo', _runner_cancellable)
            await asyncio.sleep(0.05)
            center.cancel(snapshot['id'])
            await asyncio.sleep(0.05)

            record = center.get(snapshot['id'])
            assert record is not None
            assert record.status == STATUS_CANCELLED

        asyncio.run(run())

    def test_task_cancelled_error_is_exception(self):
        """TaskCancelledError 是可捕获的异常类型。"""
        assert issubclass(TaskCancelledError, Exception)
