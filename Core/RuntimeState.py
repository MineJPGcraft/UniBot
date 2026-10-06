"""
运行时共享状态（替代旧的模块级 `Globals`）。

集中收口框架运行期的可变全局状态：内置服务实例引用、兼容模式玩家缓存、
认证令牌。这些状态由内置扩展在其启停生命周期内维护，既非配置也非持久化数据，
故不放入 Config 或 Data。

经单例 `runtime_state` 访问，不再散落为模块级可写变量。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Core.Builtin.Services.Background import BackgroundService
    from Core.Builtin.Services.Players import PlayerService
    from Core.Builtin.Services.Servers import ServerService


class RuntimeState:
    """运行期共享状态容器（单例 `runtime_state`）。"""

    def __init__(self) -> None:
        # 兼容模式下的玩家列表缓存：{服务器名称: [玩家名列表]}
        self.player_list_cache: dict[str, list[str]] = {}
        # 当前有效的认证令牌，由 Token 插件在启动时生成、使用后刷新
        self.auth_token: str = ''
        # 玩家绑定服务，由 Players 内置扩展在启停时维护
        self.player_service: PlayerService | None = None
        # Minecraft 服务器服务，由 Servers 内置扩展在启停时维护
        self.server_service: ServerService | None = None
        # 后台事务调度服务，由 Background 内置扩展在启停时维护
        self.background_service: BackgroundService | None = None


runtime_state = RuntimeState()
