from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Scripts.Extensions.Builtin.Services.Players import PlayerService
    from Scripts.Extensions.Builtin.Services.Servers import ServerService
    from Scripts.Extensions.Builtin.Services.Task import TaskService

# 兼容模式下的玩家列表缓存：{服务器名称: [玩家名列表]}
player_list_cache: dict[str, list[str]] = {}

# 当前有效的认证令牌，由 Token 插件在启动时生成、使用后刷新
auth_token: str = ''

# 玩家绑定服务，由 Players 内置扩展在启停时维护
player_service: 'PlayerService | None' = None

# Minecraft 服务器服务，由 Servers 内置扩展在启停时维护
server_service: 'ServerService | None' = None

# 定时任务服务，由 Task 内置扩展在启停时维护
task_service: 'TaskService | None' = None
