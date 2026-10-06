"""BackgroundService 测试：代理全局 background_manager 单例的调度能力。"""

import asyncio

from Core.Builtin.Services.Background import BackgroundService
from Core.Managers import background_manager
from Core.RuntimeState import runtime_state


def test_background_service_proxies_global_manager() -> None:
    """服务应代理全局 background_manager 单例，不复制调度状态。"""
    service = BackgroundService()
    assert service.started is background_manager.started
    assert service.job_names == background_manager.job_names


def test_background_service_add_and_remove() -> None:
    """add / remove 应透传全局 background_manager。"""
    service = BackgroundService()

    async def noop():
        return None

    assert service.add('svc-job', noop, 10)
    assert 'svc-job' in service.job_names
    assert service.get('svc-job') is not None
    assert service.remove('svc-job')
    assert not service.remove('svc-job')
    assert 'svc-job' not in service.job_names


def test_background_service_add_once() -> None:
    """add_once 应注册一次性事务并自动注销。"""
    service = BackgroundService()
    calls = []

    async def delayed():
        calls.append(1)

    assert service.add_once('svc-once', delayed, 0.02)

    async def run():
        await service.on_enable()
        await asyncio.sleep(0.1)
        await service.on_disable()

    asyncio.run(run())
    assert calls == [1]
    assert 'svc-once' not in service.job_names


def test_background_service_enable_disable_manages_global() -> None:
    """on_enable 应启动全局调度并登记 runtime_state，on_disable 应停止并清理。"""
    service = BackgroundService()

    async def run():
        await service.on_enable()
        assert runtime_state.background_service is service
        assert background_manager.started is True
        await service.on_disable()
        assert runtime_state.background_service is None
        assert background_manager.started is False

    asyncio.run(run())


def test_background_service_status_and_individual_control() -> None:
    """status / start_job / stop_job 应透传全局 background_manager。"""
    service = BackgroundService()
    calls = []

    async def job():
        calls.append(1)

    service.add('svc-ctrl', job, 10, immediate=True)

    async def run():
        await service.on_enable()
        # on_enable 已启动全局调度，事务自动进入运行，start_job 应返回 False
        assert not service.start_job('svc-ctrl')
        await asyncio.sleep(0.01)
        assert service.status()['svc-ctrl']['running'] is True
        assert service.stop_job('svc-ctrl')
        assert not service.stop_job('svc-ctrl')
        await service.on_disable()

    asyncio.run(run())
    assert calls == [1]
    assert 'svc-ctrl' in service.job_names
