"""BackgroundManager 测试：注册校验、周期调度、异常隔离、一次性事务与停止恢复。"""

import asyncio

from Core.Managers import background_manager as global_background_manager
from Core.Managers.Background import BackgroundManager


def test_registration_validation():
    """重复名称与非法间隔的注册应被拒绝。"""

    async def noop():
        return None

    manager = BackgroundManager()
    assert manager.add('job', noop, 10)
    assert not manager.add('job', noop, 10)
    assert not manager.add('bad', noop, 0)
    assert not manager.add('bad', noop, -1)
    assert manager.job_names == ['job']
    assert not manager.started


def test_periodic_execution_with_immediate():
    """immediate 事务应先执行一次，随后按间隔重复调度。"""
    manager = BackgroundManager()
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
    """事务体抛出异常时仅记录告警，后续调度继续进行。"""
    manager = BackgroundManager()
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


def test_once_job_runs_exactly_and_unregisters():
    """一次性事务延迟后仅执行一次并自动注销。"""
    manager = BackgroundManager()
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
    assert 'delayed' not in manager.job_names
    assert manager.get('delayed') is None


def test_stop_cancels_and_restart_resumes():
    """停止后事务不再执行，注册信息保留且可重启恢复。"""
    manager = BackgroundManager()
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
        assert 'job' in manager.job_names
        await manager.start()
        await asyncio.sleep(0.06)
        await manager.stop()

    asyncio.run(run())
    assert len(calls) > 3


def test_remove_stops_running_job():
    """注销运行中的事务应立即停止其调度。"""
    manager = BackgroundManager()
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
    assert manager.job_names == []


def test_individual_start_and_stop_job():
    """单个事务的独立启停不影响其他事务与整体状态。"""
    manager = BackgroundManager()
    calls = []

    async def job():
        calls.append(1)

    manager.add('job', job, 10, immediate=True)

    async def run():
        assert manager.start_job('job')
        assert not manager.start_job('job')
        assert not manager.start_job('missing')
        await asyncio.sleep(0.01)
        assert manager.stop_job('job')
        assert not manager.stop_job('job')

    asyncio.run(run())
    assert calls == [1]
    assert 'job' in manager.job_names
    assert manager.status()['job']['running'] is False


def test_register_after_start_auto_schedules():
    """调度器启动后新注册的事务应立即进入调度。"""
    manager = BackgroundManager()

    async def noop():
        return None

    async def run():
        await manager.start()
        assert manager.add('late', noop, 10)
        assert manager.get('late').running is True
        await manager.stop()

    asyncio.run(run())


def test_global_singleton_registered_type():
    """全局单例应为 BackgroundManager 实例且初始未启动。"""
    assert isinstance(global_background_manager, BackgroundManager)
    assert global_background_manager.started is False
