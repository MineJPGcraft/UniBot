"""内置扩展：在线玩家列表指令。"""

import asyncio
from pathlib import Path
from typing import override

from nonebot_plugin_alconna import Match

from Scripts import Globals
from Scripts.Config import config
from Scripts.Extensions import Command, Extension, FileAsset
from Scripts.Globals import player_list_cache
from Scripts.Managers import cache_manager
from Scripts.Messages import messages
from Scripts.Network import fetch_player_avatars
from Scripts.Utils import turn_message_text

extension = Extension(id='List', name=messages.builtin_extensions.list, version='1.0.0', types=('command',))


@extension.register_command
class ListCommand(Command):
    """查看服务器在线玩家列表。"""

    name = 'list'
    description = messages.commands.list.description
    usage = messages.commands.list.usage

    @override
    def declare(self) -> None:
        self.register_option('server', str, description=messages.commands.list.option_server)

    @override
    async def handler(self, server: Match[str]):
        server_flag = server.result if server.available else None
        _, response = await self.get_players(server_flag)
        if not isinstance(response, dict):
            return response
        return await turn_message_text(self.list_handler(response))

    @override
    async def image_handler(self, server: Match[str]) -> bytes | None:
        """渲染在线玩家列表为图片，返回 PNG 字节（由框架在图像模式发送）。"""
        server_flag = server.result if server.available else None
        _, response = await self.get_players(server_flag)
        if not isinstance(response, dict):
            return response
        player_names = {name for groups in response.values() for name in groups[0]}
        avatars = await self.ensure_avatars(list(player_names))
        # 头像为本地文件，用 FileAsset 包装，由渲染器决定如何引用（如 html2pic 需 file:// 前缀）
        wrapped_avatars = {name: FileAsset(Path(path)) for name, path in avatars.items()}
        return await extension.render_image(
            'List',
            (600, 800),
            context={'player_list': response, 'avatars': wrapped_avatars},
        )

    async def ensure_avatars(self, player_names: list):
        """获取玩家头像文件路径：本地已缓存直接复用，缺失的下载后落盘。"""
        cached, missing_names = cache_manager.get_cached(player_names)
        if not missing_names:
            return cached
        contents = await fetch_player_avatars(missing_names)
        files = {cache_manager.get_path(name).name: content for name, (content, _) in contents.items()}
        saved = await cache_manager.save_all(files)
        for name in contents:
            cached[name] = saved[cache_manager.get_path(name).name]
        return cached

    def split_players(self, players: list):
        """将玩家列表按假人前缀分为 (真实玩家, 假人) 两组，未配置前缀时全部视为真实玩家。"""
        if not config.bot_prefix:
            return list(players), []
        real_players, fake_players = [], []
        for player in players:
            if player.upper().startswith(config.bot_prefix):
                fake_players.append(player)
                continue
            real_players.append(player)
        return real_players, fake_players

    async def get_players(self, server_flag: str | None = None):
        """查询在线玩家列表：指定服务器查单个，否则查询全部已连接服务器。"""
        server_service = Globals.server_service
        if server_service is None:
            return False, messages.commands.list.no_server
        if server_flag:
            server = server_service.get_server(server_flag)
            if server is None:
                return False, messages.commands.list.server_not_found.format(server=server_flag)
            return True, {server.self_id: await self.query_server_players(server, server.self_id)}
        if not server_service.servers:
            return False, messages.commands.list.no_server
        results = await asyncio.gather(
            *(self.query_server_players(server, name) for name, server in server_service.servers.items())
        )
        players = dict(zip(server_service.servers, results))
        return True, players

    async def query_server_players(self, server, server_name: str):
        """查询单个服务器的玩家并分组：兼容模式读取缓存，否则实时查询。"""
        if config.list_compatible_mode:
            cached = player_list_cache.get(server_name, [])
            return self.split_players(list(cached))
        server_service = Globals.server_service
        player_list, _ = await server_service.get_player_list(server)
        return self.split_players(player_list)

    def list_handler(self, players: dict):
        """将玩家列表数据格式化为文本消息（异步生成器）。"""
        if not players:
            yield messages.commands.list.no_server
            return
        if len(players) == 1:
            server_name, players_data = next(iter(players.items()))
            yield messages.commands.list.single_title.format(server=server_name)
            yield from self.format_players(players_data)
            total = sum(len(group) for group in players_data)
            yield messages.commands.list.player_total.format(count=total)
            return
        player_count = 0
        yield messages.commands.list.global_title
        for name, players_data in players.items():
            player_count += sum(len(group) for group in players_data)
            yield messages.commands.list.server_divider.format(name=name)
            yield from self.format_players(players_data)
        yield messages.commands.list.player_total.format(count=player_count)

    def format_players(self, players: list):
        """格式化单个服务器的玩家分组为文本。"""
        real_players, fake_players = players
        if config.bot_prefix:
            yield messages.commands.list.player_section
            yield '    ' + ('\n    '.join(real_players) if real_players else messages.commands.list.no_player)
            yield messages.commands.list.fake_section
            yield '    ' + ('\n    '.join(fake_players) if fake_players else messages.commands.list.no_fake) + '\n'
            return
        if real_players:
            yield '    ' + '\n    '.join(real_players) + '\n'
            return
        yield '  ' + messages.commands.list.no_player + '\n'
