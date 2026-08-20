"""Minecraft 事件通知测试。"""

import asyncio
from types import SimpleNamespace

from Scripts import Globals
from Scripts.Plugins import Events


class _ServerService:
    def __init__(self) -> None:
        self.broadcasts = []

    async def broadcast(self, message, except_server: str = '') -> None:
        self.broadcasts.append((message, except_server))


def _achievement_event(*, translated: str | None, title: str | None = None, key: str | None = None):
    display = SimpleNamespace(title=SimpleNamespace(text=title)) if title else None
    translate = SimpleNamespace(text=translated) if translated else None
    return SimpleNamespace(
        server_name='survival',
        player=SimpleNamespace(nickname='Steve'),
        achievement=SimpleNamespace(translate=translate, display=display, key=key),
    )


def test_achievement_notification_uses_translated_message(monkeypatch) -> None:
    group_messages = []
    server_service = _ServerService()

    async def send_to_groups(message: str) -> bool:
        group_messages.append(message)
        return True

    monkeypatch.setattr(Events, 'send_message_to_groups', send_to_groups)
    monkeypatch.setattr(Events, 'build_server_message', lambda source, player, content: (source, player, content))
    monkeypatch.setattr(Globals, 'server_service', server_service)
    monkeypatch.setattr(Events.config, 'bot_prefix', '')
    monkeypatch.setattr(Events.config, 'broadcast_player', True)
    monkeypatch.setattr(Events.config, 'sync_message_between_servers', True)

    event = _achievement_event(translated='Steve 达成了进度 [石器时代]')
    asyncio.run(Events.handle_player_achievement(event))

    assert group_messages == ['Steve 达成了进度 [石器时代]']
    assert server_service.broadcasts == [(('survival', 'Steve', 'Steve 达成了进度 [石器时代]'), 'survival')]


def test_achievement_notification_falls_back_to_title(monkeypatch) -> None:
    group_messages = []

    async def send_to_groups(message: str) -> bool:
        group_messages.append(message)
        return True

    monkeypatch.setattr(Events, 'send_message_to_groups', send_to_groups)
    monkeypatch.setattr(Events.config, 'bot_prefix', '')
    monkeypatch.setattr(Events.config, 'broadcast_player', True)
    monkeypatch.setattr(Events.config, 'sync_message_between_servers', False)

    event = _achievement_event(translated=None, title='石器时代', key='minecraft:story/mine_stone')
    asyncio.run(Events.handle_player_achievement(event))

    assert group_messages == ['Steve 达成了成就 [石器时代]']
