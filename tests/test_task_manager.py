"""TaskManager 测试：注册校验、周期调度、异常隔离、一次性任务与停止恢复。"""

import asyncio

from Scripts.Managers import task_manager as global_task_manager
from Scripts.Managers.Task import TaskManager


def test_registration_validation():
    """重复名称与非法间隔的注册应被拒绝。"""

    async def noop():
        return None

    manager = TaskManager()
    assert manager.add('job', noop, 10)
    assert not manager.add('job', noop, 10)
    assert not manager.add('bad', noop, 0)
    assert not manager.add('bad', noop, -1)
    assert manager.task_names == ['job']
    assert not manager.started


def test_periodic_execution_with_immediate():
    """immediate 任务应先执行一次，随后按间隔重复调度。"""
    manager = TaskManager()
    ticks = []

    async def job():
        ticks.append(1)

    manager.add('ticker', job, 0.05, immediate=True)

    async def run():
        await manager.start()
        assert manager.status()['ticker']['running'] is True
        await asyncio.sleep(0.16)
        await manager.stop()

    asyncio.run(run())
    assert len(ticks) >= 2
    assert not manager.started


def test_exception_isolation_keeps_loop_alive():
    """任务体抛出异常时仅记录告警，后续调度继续进行。"""
    manager = TaskManager()
    calls = []

    async def flaky():
        calls.append(1)
        raise RuntimeError('boom')

    manager.add('flaky', flaky, 0.02, immediate=True)

    async def run():
        await manager.start()
        await asyncio.sleep(0.08)
        status = manager.status()['flaky']
        await manager.stop()
        assert status['running'] is True

    asyncio.run(run())
    assert len(calls) >= 2


def test_once_task_runs_exactly_and_unregisters():
    """一次性任务延迟后仅执行一次并自动注销。"""
    manager = TaskManager()
    calls = []

    async def delayed():
        calls.append(1)

    assert manager.add_once('delayed', delayed, 0.03)

    async def run():
        await manager.start()
        await asyncio.sleep(0.12)
        await manager.stop()

    asyncio.run(run())
    assert calls == [1]
    assert 'delayed' not in manager.task_names
    assert manager.get('delayed') is None


def test_stop_cancels_and_restart_resumes():
    """停止后任务不再执行，注册信息保留且可重启恢复。"""
    manager = TaskManager()
    calls = []

    async def job():
        calls.append(1)

    manager.add('job', job, 0.02, immediate=True)

    async def run():
        await manager.start()
        await asyncio.sleep(0.06)
        await manager.stop()
        frozen = len(calls)
        await asyncio.sleep(0.08)
        assert len(calls) == frozen
        assert 'job' in manager.task_names
        await manager.start()
        await asyncio.sleep(0.06)
        await manager.stop()

    asyncio.run(run())
    assert len(calls) > 3


def test_remove_stops_running_task():
    """注销运行中的任务应立即停止其调度。"""
    manager = TaskManager()
    calls = []

    async def job():
        calls.append(1)

    manager.add('job', job, 0.02, immediate=True)

    async def run():
        await manager.start()
        await asyncio.sleep(0.03)
        assert manager.remove('job')
        assert not manager.remove('job')
        frozen = len(calls)
        await asyncio.sleep(0.06)
        assert len(calls) == frozen

    asyncio.run(run())
    assert manager.task_names == []


def test_individual_start_and_stop_task():
    """单个任务的独立启停不影响其他任务与整体状态。"""
    manager = TaskManager()
    calls = []

    async def job():
        calls.append(1)

    manager.add('job', job, 10, immediate=True)

    async def run():
        assert manager.start_task('job')
        assert not manager.start_task('job')
        assert not manager.start_task('missing')
        await asyncio.sleep(0.01)
        assert manager.stop_task('job')
        assert not manager.stop_task('job')

    asyncio.run(run())
    assert calls == [1]
    assert 'job' in manager.task_names
    assert manager.status()['job']['running'] is False


def test_register_after_start_auto_schedules():
    """管理器启动后新注册的任务应立即进入调度。"""
    manager = TaskManager()

    async def noop():
        return None

    async def run():
        await manager.start()
        assert manager.add('late', noop, 10)
        assert manager.get('late').running is True
        await manager.stop()

    asyncio.run(run())


def test_global_singleton_registered_type():
    """全局单例应为 TaskManager 实例且初始未启动。"""
    assert isinstance(global_task_manager, TaskManager)
    assert global_task_manager.started is False
