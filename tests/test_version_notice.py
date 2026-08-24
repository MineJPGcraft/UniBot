"""版本更新群提醒测试。"""

import asyncio

from Scripts import Utils
from Scripts.Config import config
from Scripts.Managers.Version import VersionManager

NOTICE_MESSAGE = '检测到新版本 2.0.0，请及时更新！'


def _manager(version: str = '1.0.0', latest: str | None = None) -> VersionManager:
    """构建携带指定版本的全新管理器实例，避免用例间共享提醒状态。"""
    manager = VersionManager()
    manager.version = version
    manager.latest_version = latest
    return manager


def _patch_sender(monkeypatch, result: bool = True) -> list[str]:
    """替换群消息发送实现并记录调用，返回记录列表。"""
    sent_messages: list[str] = []

    async def send_to_groups(message: str) -> bool:
        sent_messages.append(message)
        return result

    monkeypatch.setattr(Utils, 'send_message_to_groups', send_to_groups)
    return sent_messages


def test_notify_skipped_when_switch_off(monkeypatch) -> None:
    sent = _patch_sender(monkeypatch)
    monkeypatch.setattr(config, 'broadcast_update', False)
    asyncio.run(_manager(latest='2.0.0').try_notify_update())
    assert sent == []


def test_notify_sends_once_per_version(monkeypatch) -> None:
    sent = _patch_sender(monkeypatch)
    monkeypatch.setattr(config, 'broadcast_update', True)
    manager = _manager(latest='2.0.0')
    asyncio.run(manager.try_notify_update())
    asyncio.run(manager.try_notify_update())
    assert sent == [NOTICE_MESSAGE]
    assert manager.notified_version == '2.0.0'


def test_notify_retries_after_send_failure(monkeypatch) -> None:
    failed_attempts = _patch_sender(monkeypatch, result=False)
    monkeypatch.setattr(config, 'broadcast_update', True)
    manager = _manager(latest='2.0.0')
    asyncio.run(manager.try_notify_update())
    assert failed_attempts == [NOTICE_MESSAGE]

    retried_messages = _patch_sender(monkeypatch, result=True)
    asyncio.run(manager.try_notify_update())
    assert retried_messages == [NOTICE_MESSAGE]


def test_notify_skipped_without_update(monkeypatch) -> None:
    sent = _patch_sender(monkeypatch)
    monkeypatch.setattr(config, 'broadcast_update', True)
    asyncio.run(_manager().try_notify_update())
    assert sent == []


def test_check_update_compares_semantically() -> None:
    """版本比较按 PEP 440 语义进行，而非字符串不等式。"""
    # 落后于最新版本
    assert _manager(version='v1.0.3', latest='v1.1.0').check_update()
    # 相同版本（含 v 前缀差异）不算更新
    assert not _manager(version='v1.0.3', latest='v1.0.3').check_update()
    assert not _manager(version='v1.0.3', latest='1.0.3').check_update()
    # 本地版本比远端新（回滚场景）
    assert not _manager(version='v2.0.0', latest='v1.0.3').check_update()
    # 预发布版本语义：alpha < 正式版
    assert _manager(version='v1.0.3', latest='v1.0.4-alpha').check_update()


def test_check_update_falls_back_for_unparsable_versions() -> None:
    """无法解析为 PEP 440 版本号时回退为字符串不等式。"""
    assert _manager(version='dev-build', latest='not-a-version').check_update()
    assert not _manager(version='dev-build', latest='dev-build').check_update()
    # 任一版本缺失时不提示更新
    assert not _manager(version='v1.0.0', latest=None).check_update()
    assert not _manager(version='', latest='v9.9.9').check_update()
