"""玩家绑定服务测试：内存缓存与持久化。"""

import asyncio
from typing import Any

from Core.Builtin.Services.Players import PlayerService, extension
from Core.RuntimeState import runtime_state


class _DataStore:
    """记录玩家数据读写次数的测试存储。"""

    def __init__(self, data: Any) -> None:
        self.data = data
        self.read_count = 0
        self.write_count = 0

    def read_json(self, relative: str) -> dict[str, list[str]]:
        self.read_count += 1
        return self.data

    def write_json(self, relative: str, data: Any) -> None:
        self.write_count += 1
        self.data = data


class _MissingDataStore(_DataStore):
    """模拟首次启动时玩家数据文件尚未创建。"""

    def __init__(self) -> None:
        super().__init__(None)

    def read_json(self, relative: str) -> dict[str, list[str]]:
        self.read_count += 1
        raise FileNotFoundError(relative)


def test_player_service_creates_missing_data_file(monkeypatch) -> None:
    store = _MissingDataStore()
    monkeypatch.setattr(extension, '_data', store)
    monkeypatch.setattr(extension, '_bound', True)
    service = PlayerService()

    asyncio.run(service.on_enable())

    assert runtime_state.player_service is service
    assert service.players == {}
    assert store.read_count == 1
    assert store.write_count == 1
    assert store.data == {'accounts': {}, 'players': []}


def test_player_service_uses_memory_cache(monkeypatch) -> None:
    store = _DataStore({'10001': ['Steve']})
    monkeypatch.setattr(extension, '_data', store)
    monkeypatch.setattr(extension, '_bound', True)
    service = PlayerService()

    asyncio.run(service.on_enable())
    assert runtime_state.player_service is service
    assert service.players == {'10001': ['Steve']}
    assert store.data == {
        'accounts': {'qq_api:10001': 0},
        'players': [['Steve']],
    }
    assert asyncio.run(service.check_player_occupied('steve')) is True
    assert store.read_count == 1
    assert store.write_count == 1

    assert asyncio.run(service.append_player('10002', 'Alex')) is True
    assert service.players == {'10001': ['Steve'], '10002': ['Alex']}
    assert store.read_count == 1
    assert store.write_count == 2
    assert store.data == {
        'accounts': {'qq_api:10001': 0, 'qq_api:10002': 1},
        'players': [['Steve'], ['Alex']],
    }

    asyncio.run(service.on_disable())
    assert runtime_state.player_service is None
    assert service.players == {}


def test_player_service_loads_current_data_without_rewriting(monkeypatch) -> None:
    store = _DataStore(
        {
            'accounts': {'qq_api:10001': 0, 'qq_client:20001': 1},
            'players': [['Steve'], ['Alex']],
        }
    )
    monkeypatch.setattr(extension, '_data', store)
    monkeypatch.setattr(extension, '_bound', True)
    service = PlayerService()

    asyncio.run(service.on_enable())

    assert service.players == {
        '10001': ['Steve'],
        'qq_client:20001': ['Alex'],
    }
    assert store.read_count == 1
    assert store.write_count == 0


def test_remove_player_compacts_unreferenced_group(monkeypatch) -> None:
    store = _DataStore(
        {
            'accounts': {'qq_api:10001': 0, 'qq_api:10002': 1},
            'players': [['Steve'], ['Alex']],
        }
    )
    monkeypatch.setattr(extension, '_data', store)
    monkeypatch.setattr(extension, '_bound', True)
    service = PlayerService()
    asyncio.run(service.on_enable())

    assert asyncio.run(service.remove_player('10001')) == ['Steve']
    assert service.players == {'10002': ['Alex']}
    assert store.data == {
        'accounts': {'qq_api:10002': 0},
        'players': [['Alex']],
    }
