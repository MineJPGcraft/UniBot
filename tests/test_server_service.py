"""Minecraft 服务器 API 服务测试。"""

import asyncio
from typing import Any

from Core.Builtin.Services import Servers
from Core.Extension import extension_manager
from Core.RuntimeState import runtime_state


class _Adapter:
    """测试用 Minecraft 适配器。"""

    def __init__(self, bots: dict[str, Any]) -> None:
        self.bots = bots


class _Bot:
    """测试用 Minecraft Bot。"""

    def __init__(self, self_id: str) -> None:
        self.self_id = self_id


class _RconBot(_Bot):
    """测试用支持 RCON 的 Minecraft Bot。"""

    async def send_rcon_command(self, command: str) -> str:
        return f'§6已执行 {command}：§cOK'


def test_server_service_lifecycle_and_selection(monkeypatch) -> None:
    first = _Bot('survival')
    second = _Bot('creative')
    monkeypatch.setattr(
        Servers,
        'get_adapter',
        lambda adapter_type: _Adapter(
            {
                first.self_id: first,
                second.self_id: second,
            }
        ),
    )
    service = Servers.ServerService()

    asyncio.run(service.on_enable())

    assert service.name == 'server'
    assert runtime_state.server_service is service
    assert service.check_online() is True
    assert service.get_server(1) is first
    assert service.get_server('2') is second
    assert service.get_server('creative') is second
    assert service.get_server('missing') is None

    asyncio.run(service.on_disable())
    assert service.check_online() is False
    assert runtime_state.server_service is None


def test_server_service_is_registered() -> None:
    extension_manager.load()

    service = extension_manager.get_service('server')

    assert isinstance(service, Servers.ServerService)


def test_execute_strips_color() -> None:
    service = Servers.ServerService()
    service.servers = {'survival': _RconBot('survival')}

    result = asyncio.run(service.execute('fake_command'))

    assert result == {'survival': '已执行 fake_command：OK'}


def test_execute_failure_returns_none() -> None:
    class _FailBot(_Bot):
        async def send_rcon_command(self, command: str) -> str:
            raise RuntimeError('boom')

    service = Servers.ServerService()
    service.servers = {'survival': _FailBot('survival')}

    result = asyncio.run(service.execute('fake_command'))

    assert result == {'survival': None}


def test_execute_empty_servers_returns_empty_dict() -> None:
    service = Servers.ServerService()
    service.servers = {}

    result = asyncio.run(service.execute('fake_command'))

    assert result == {}


def test_execute_broadcast_collects_failures() -> None:
    class _FailBot(_Bot):
        async def send_rcon_command(self, command: str) -> str:
            raise RuntimeError('boom')

    service = Servers.ServerService()
    service.servers = {'good': _RconBot('good'), 'bad': _FailBot('bad')}

    results = asyncio.run(service.execute('fake_command'))

    assert results == {'good': '已执行 fake_command：OK', 'bad': None}


def test_get_player_list_strips_color() -> None:
    class _ListBot(_Bot):
        async def send_rcon_command(self, command: str) -> str:
            return '§6There are §a3 of a max of §c10 players online: §balice, §dbob, §ecarol'

    players, max_players = asyncio.run(Servers.ServerService().get_player_list(_ListBot('survival')))

    assert players == ['alice', 'bob', 'carol']
    assert max_players == 10
