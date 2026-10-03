"""
内置服务：玩家绑定数据管理。

把玩家绑定数据从 DataManager 抽取为内置 API 服务，供内置命令、事件处理器与
WebUI API 通过 `extension.api.get(PlayerService)`（或全局注册名 `player`）获取。
数据经内置扩展的目录式存储直接落盘为 `Data/Players.json`。
"""

from typing import Any, TypedDict, override

from Scripts import Globals
from Scripts.Config import config
from Scripts.Extensions import Extension, Service
from Scripts.Messages import messages

# 创建唯一扩展实例，能力经实例装饰器登记
# 内置扩展数据存储指向 Data 根目录，Player 扩展读写 `Player.json`
extension = Extension(id='Players', name=messages.builtin_extensions.players, version='1.0.0', types=('api',))

# 玩家绑定数据文件名（位于 Data 根目录）
DATA_FILE = 'Players.json'
DEFAULT_ACCOUNT_PLATFORM = 'qq_api'


class PlayerData(TypedDict):
    """玩家绑定数据持久化结构。"""

    accounts: dict[str, int]
    players: list[list[str]]


@extension.register_service
class PlayerService(Service):
    """管理用户与游戏 ID 的绑定关系，数据同源落盘 `Data/Players.json`。"""

    name = 'player'

    def __init__(self) -> None:
        self._accounts: dict[str, int] = {}
        self._players: list[list[str]] = []

    @property
    def players(self) -> dict[str, list[str]]:
        """按当前兼容格式返回全部绑定关系：{user_id: [player, ...]}。"""
        return {self._display_account(account): self._players[index] for account, index in self._accounts.items()}

    @override
    async def on_enable(self) -> None:
        """服务启动时将绑定数据加载到内存。"""
        store = extension.data
        try:
            data = store.read_json(DATA_FILE) or {}
        except FileNotFoundError:
            data = {}
        current_data = self._parse_current_data(data)
        if current_data is not None:
            self._accounts = dict(current_data['accounts'])
            self._players = [list(players) for players in current_data['players']]
            Globals.player_service = self
            return
        self._migrate_legacy_data(data)
        Globals.player_service = self

    @override
    async def on_disable(self) -> None:
        """服务关闭时释放内存缓存。"""
        if Globals.player_service is self:
            Globals.player_service = None
        self._accounts.clear()
        self._players.clear()

    @staticmethod
    def _parse_current_data(data: Any) -> PlayerData | None:
        """校验并解析 accounts + players 数据结构。"""
        if not isinstance(data, dict):
            return None
        accounts = data.get('accounts')
        players = data.get('players')
        if not isinstance(accounts, dict) or not isinstance(players, list):
            return None
        if not all(isinstance(account, str) and isinstance(index, int) for account, index in accounts.items()):
            return None
        if not all(isinstance(group, list) and all(isinstance(player, str) for player in group) for group in players):
            return None
        if any(index < 0 or index >= len(players) for index in accounts.values()):
            return None
        return {
            'accounts': dict(accounts),
            'players': [list(group) for group in players],
        }

    @staticmethod
    def _account_key(account: str) -> str:
        """将当前裸账号兼容为带平台前缀的账号键。"""
        if ':' in account:
            return account
        return f'{DEFAULT_ACCOUNT_PLATFORM}:{account}'

    @staticmethod
    def _display_account(account: str) -> str:
        """当前 QQ API 账号对外保持裸 ID，其它平台保留完整账号键。"""
        prefix = f'{DEFAULT_ACCOUNT_PLATFORM}:'
        if account.startswith(prefix):
            return account.removeprefix(prefix)
        return account

    def _migrate_legacy_data(self, data: Any) -> None:
        """将旧版 {user_id: [player]} 数据迁移为索引结构。"""
        legacy_data = data if isinstance(data, dict) else {}
        accounts: dict[str, int] = {}
        players: list[list[str]] = []
        for account, bounded_players in legacy_data.items():
            if not isinstance(account, str) or not isinstance(bounded_players, list):
                continue
            accounts[self._account_key(account)] = len(players)
            players.append([str(player) for player in bounded_players])
        self._save(accounts, players)

    def _save(self, accounts: dict[str, int], players: list[list[str]]) -> None:
        """原子保存绑定数据，并在成功后更新内存缓存。"""
        store = extension.data
        store.write_json(DATA_FILE, {'accounts': accounts, 'players': players})
        self._accounts = accounts
        self._players = players

    async def append_player(self, user: str, player: str) -> bool:
        """为用户追加一个玩家绑定，受绑定数量上限约束。"""

        account = self._account_key(user)
        accounts = dict(self._accounts)
        players = [list(bounded_players) for bounded_players in self._players]
        index = accounts.get(account)
        bounded = players[index] if index is not None else []
        if config.qq_bound_max_number > 0 and len(bounded) >= config.qq_bound_max_number:
            return False
        if index is None:
            accounts[account] = len(players)
            players.append([player])
        elif player not in bounded:
            players[index] = [*bounded, player]
        self._save(accounts, players)
        return True

    async def remove_player(self, user: str, player: str = '') -> list[str]:
        """移除用户绑定；player 为空时移除全部，返回被移除的玩家列表（空列表表示无绑定）。"""
        account = self._account_key(user)
        index = self._accounts.get(account)
        if index is None:
            return []
        accounts = dict(self._accounts)
        players = [list(bounded_players) for bounded_players in self._players]
        bounded = players[index]
        if not player and not bounded:
            return []
        removed = bounded
        if player:
            if player not in bounded:
                return []
            remaining = [p for p in bounded if p != player]
            if remaining:
                players[index] = remaining
                self._save(accounts, players)
                return [player]
            removed = [player]
        accounts.pop(account)
        if index not in accounts.values():
            players.pop(index)
            accounts = {
                bound_account: bound_index - 1 if bound_index > index else bound_index
                for bound_account, bound_index in accounts.items()
            }
        self._save(accounts, players)
        return removed

    async def check_player_occupied(self, player: str) -> bool:
        """检查游戏 ID 是否已被任意用户绑定（忽略大小写）。"""
        player = player.lower()
        return any(player in (bp.lower() for bp in bounded_players) for bounded_players in self._players)
