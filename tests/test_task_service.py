"""TaskService 测试：代理全局 task_manager 单例的调度能力。"""

import asyncio

from Scripts import Globals
from Scripts.Extensions.Builtin.Services.Task import TaskService
from Scripts.Managers import task_manager


def test_task_service_proxies_global_manager() -> None:
    """服务应代理全局 task_manager 单例，不复制调度状态。"""
    service = TaskService()
    assert service.started is task_manager.started
    assert service.task_names == task_manager.task_names


def test_task_service_add_and_remove() -> None:
    """add / remove 应透传全局 task_manager。"""
    service = TaskService()

    async def noop():
        return None

    assert service.add('svc-job', noop, 10)
    assert 'svc-job' in service.task_names
    assert service.get('svc-job') is not None
    assert service.remove('svc-job')
    assert not service.remove('svc-job')
    assert 'svc-job' not in service.task_names


def test_task_service_add_once() -> None:
    """add_once 应注册一次性任务并自动注销。"""
    service = TaskService()
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
    assert 'svc-once' not in service.task_names


def test_task_service_enable_disable_manages_global() -> None:
    """on_enable 应启动全局调度并登记 Globals，on_disable 应停止并清理。"""
    service = TaskService()

    async def run():
        await service.on_enable()
        assert Globals.task_service is service
        assert task_manager.started is True
        await service.on_disable()
        assert Globals.task_service is None
        assert task_manager.started is False

    asyncio.run(run())


def test_task_service_status_and_individual_control() -> None:
    """status / start_task / stop_task 应透传全局 task_manager。"""
    service = TaskService()
    calls = []

    async def job():
        calls.append(1)

    service.add('svc-ctrl', job, 10, immediate=True)

    async def run():
        await service.on_enable()
        # on_enable 已启动全局调度，任务自动进入运行，start_task 应返回 False
        assert not service.start_task('svc-ctrl')
        await asyncio.sleep(0.01)
        assert service.status()['svc-ctrl']['running'] is True
        assert service.stop_task('svc-ctrl')
        assert not service.stop_task('svc-ctrl')
        await service.on_disable()

    asyncio.run(run())
    assert calls == [1]
    assert 'svc-ctrl' in service.task_names