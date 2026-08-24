"""内置服务：Minecraft 服务器交互。"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Coroutine, Concatenate, ParamSpec, TypeVar, override

from nonebot import get_adapter
from nonebot.adapters.minecraft import Adapter as MCAdapter
from nonebot.adapters.minecraft import Bot
from nonebot.adapters.minecraft.message import Message

from Scripts import Globals
from Scripts.Extensions import Extension, Service
from Scripts.Logging import logger
from Scripts.Utils import strip_minecraft_color

extension = Extension(id='Servers', name='Minecraft 服务器服务', version='1.0.0', types=('api',))

R = TypeVar('R')
P = ParamSpec('P')


def collect_results(
    func: Callable[Concatenate[Any, Bot, P], Awaitable[R]],
) -> Callable[Concatenate[Any, P], Awaitable[dict[str, R]]]:
    """并发向所有服务器分发任务并收集为 {名称: 结果} 字典，注入 server 参数。"""

    @wraps(func)
    async def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> dict[str, R]:
        names: list[str] = []
        tasks: list[Awaitable[R]] = []
        for name, server in self.servers.items():
            names.append(name)
            tasks.append(func(self, server, *args, **kwargs))
        results = await asyncio.gather(*tasks)
        return {names[index]: result for index, result in enumerate(results)}

    return wrapper


@extension.register_service
class ServerService(Service):
    """封装 Minecraft 服务器查询、指令执行与消息广播能力。"""

    name = 'server'

    def __init__(self) -> None:
        self.servers: dict[str, Bot] = {}

    @override
    async def on_enable(self) -> None:
        """服务启动时绑定 Minecraft 适配器的机器人集合。"""
        adapter = get_adapter(MCAdapter)
        self.servers = adapter.bots  # pyright: ignore[reportAttributeAccessIssue]
        Globals.server_service = self

    @override
    async def on_disable(self) -> None:
        """服务关闭时释放适配器机器人集合引用。"""
        if Globals.server_service is self:
            Globals.server_service = None
        self.servers = {}

    def get_server(self, server_flag: str | int) -> Bot | None:
        """通过名称或编号获取 Minecraft 机器人（编号从 1 开始）。"""
        if isinstance(server_flag, int) or server_flag.isdigit():
            index, names = int(server_flag), list(self.servers.keys())
            if 0 < index <= len(names):
                return self.servers[names[index - 1]]
        return self.servers.get(str(server_flag))

    def check_online(self) -> bool:
        """是否有 Minecraft 服务器在线。"""
        return bool(self.servers)

    @collect_results
    async def execute(self, server: Bot, command: str) -> str | None:
        """向所有已连接服务器执行 Minecraft 指令，失败返回 None。"""
        try:
            result = await server.send_rcon_command(command=command)
        except Exception as error:
            logger.warning(f'Failed to send command to server [{server.self_id}]: {error}')
            return None
        return strip_minecraft_color(result) if result else ''

    async def get_status(self, server: Bot) -> dict:
        """获取 Minecraft 服务器状态。"""
        try:
            status = await server.get_status()
        except Exception as error:
            logger.warning(f'Failed to get status of server [{server.self_id}]: {error}')
            return {
                'online': False,
                'server_type': '',
                'players': 0,
                'max_players': 0,
                'version': '',
                'motd': '',
                'cpu_load': 0.0,
                'memory_percent': 0.0,
                'jvm_memory_used': 0,
                'jvm_memory_max': 0,
            }

        server_ping = status.server_list_ping
        player_status = server_ping.players
        version_status = server_ping.version
        cpu_info = status.cpu_information
        jvm_memory = status.memory_information.jvm_memory

        return {
            'online': server_ping.available,
            'server_type': status.server_type,
            'players': int(player_status.online) if player_status else 0,
            'max_players': int(player_status.max) if player_status else 0,
            'version': version_status.name if version_status else status.server_version,
            'motd': server_ping.description,
            'cpu_load': round(max(cpu_info.system_load, cpu_info.process_load), 1),
            'memory_percent': round(jvm_memory.percentage, 1),
            'jvm_memory_used': round(jvm_memory.used / 1024 / 1024, 1),
            'jvm_memory_max': round(jvm_memory.max / 1024 / 1024, 1),
        }

    async def get_player_list(self, server: Bot) -> tuple[list[str], int]:
        """通过 RCON 指令获取并解析服务器玩家列表。"""
        try:
            result = await server.send_rcon_command(command='list')
        except Exception as error:
            logger.warning(f'Failed to get player list of server [{server.self_id}]: {error}')
            return [], 0
        result = strip_minecraft_color(result) if result else result
        if not result:
            return [], 0

        match = re.search(r'^There are \d+ of (?:a )?max(?: of)? (\d+) players online:\s*(.*)$', result.strip())
        if match is None:
            logger.warning(f'Failed to parse player list of server [{server.self_id}]: {result}')
            return [], 0
        max_players = int(match.group(1))
        players = [player.strip() for player in match.group(2).split(',') if player.strip()]
        return players, max_players

    @collect_results
    async def broadcast(self, server: Bot, message: Message | str, except_server: str = '') -> None:
        """广播消息到所有服务器（除 except_server 外）。"""
        if server.self_id == except_server:
            return None
        try:
            return await server.send_msg(message=message)
        except Exception as error:
            logger.warning(f'Failed to broadcast message to server [{server.self_id}]: {error}')
