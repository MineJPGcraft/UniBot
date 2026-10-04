"""内置扩展：玩家绑定指令。"""

from typing import override

from nonebot_plugin_alconna import At, Match
from nonebot_plugin_uninfo import Uninfo

from Core.Config import config
from Core.Extension import Command, Extension, SubCommand
from Core.I18n import i18n_deferred, text
from Core.RuntimeState import runtime_state
from Core.Utils import check_player, get_permission

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Bound', name=i18n_deferred('builtin.bound.name'), version='1.0.0', types=('command',))


@extension.register_command
class BoundCommand(Command):
    """管理玩家白名单绑定。"""

    name = 'bound'
    description = i18n_deferred('core.commands.bound.description')
    usage = i18n_deferred('core.commands.bound.usage')

    @override
    def declare(self) -> None:
        self.register_option('player', str, description=i18n_deferred('core.commands.bound.option_player'))

    @override
    async def handler(self, session: Uninfo, player: Match[str]):
        """处理 .bound <player>。"""
        if not player.available:
            return text('core.commands.bound.invalid_name')
        return await self.bound_handler(session, player.result)

    async def bound_handler(self, session: Uninfo, player: str):
        """执行玩家白名单绑定。"""
        if not check_player(player):
            return text('core.commands.bound.invalid_name')
        user = str(session.user.id)
        player_service, server_service = runtime_state.player_service, runtime_state.server_service
        if player_service is None:
            return text('core.commands.bound.server_offline')
        if user in player_service.players and player in player_service.players[user]:
            return text('core.commands.bound.already_bound')
        if await player_service.check_player_occupied(player):
            return text('core.commands.bound.occupied')
        if server_service is None or not server_service.check_online():
            return text('core.commands.bound.server_offline')
        if await player_service.append_player(user, player):
            await server_service.execute(f'{config.whitelist_command} add {player}')
            return text('core.commands.bound.bound_success', name=session.user.name or user, user=user, player=player)
        return text('core.commands.bound.too_many')

    class List(SubCommand['BoundCommand']):
        """列出所有绑定。"""

        name = 'list'
        description = i18n_deferred('core.commands.bound.list_desc')

        @override
        async def handler(self, session: Uninfo):
            if not get_permission(session):
                return text('core.commands.bound.no_permission')
            player_service = runtime_state.player_service
            if player_service is None or not player_service.players:
                return text('core.commands.bound.no_binding')
            return (
                text('core.commands.bound.list_title')
                + '\n'
                + '\n'.join(f'  {user} -> {"、".join(players)}' for user, players in player_service.players.items())
            )

        @override
        async def image_handler(self, session: Uninfo) -> bytes | None:
            """渲染绑定列表为图片，返回 PNG 字节（由框架在图像模式发送）。"""
            if not get_permission(session):
                return text('core.commands.bound.no_permission')
            player_service = runtime_state.player_service
            if player_service is None or not player_service.players:
                return text('core.commands.bound.no_binding')
            bindings = [{'user': user, 'players': players} for user, players in player_service.players.items()]
            return await extension.render_image('Bound', (600, 800), context={'bindings': bindings})

    class Query(SubCommand['BoundCommand']):
        """查询指定用户的绑定。"""

        name = 'query'
        description = i18n_deferred('core.commands.bound.query_desc')

        @override
        def declare(self) -> None:
            self.register_option('user_id', At | str, description=i18n_deferred('core.commands.bound.arg_user'))

        @override
        async def handler(self, session: Uninfo, user_id: Match[At | str]):
            target_user = user_id.result if user_id.available else str(session.user.id)
            if isinstance(target_user, At):
                target_user = target_user.target
            player_service = runtime_state.player_service
            if player_service is None or target_user not in player_service.players:
                return text('core.commands.bound.not_bound_query', target_user=target_user)
            players = '、'.join(player_service.players[target_user])
            return text('core.commands.bound.query_result', target_user=target_user, players=players)

    class Remove(SubCommand['BoundCommand']):
        """移除指定绑定。"""

        name = 'remove'
        description = i18n_deferred('core.commands.bound.remove_desc')

        @override
        def declare(self) -> None:
            self.register_option('player', At | str, description=i18n_deferred('core.commands.bound.arg_player'))

        @override
        async def handler(self, session: Uninfo, player: Match[At | str]):
            current_user = str(session.user.id)
            if not player.available:
                # .bound remove - 自己解绑全部
                return await self.remove_self_all(session)
            target_user = player.result.target if isinstance(player.result, At) else player.result
            # .bound remove <QQ> - 管理员解绑用户
            if target_user != current_user and not get_permission(session):
                return text('core.commands.bound.no_permission')
            return await self.remove_user(target_user)

        async def remove_user(self, target_user: str):
            """移除指定用户绑定的所有白名单。"""
            player_service, server_service = runtime_state.player_service, runtime_state.server_service
            if player_service is None or server_service is None or not server_service.check_online():
                return text('core.commands.bound.server_offline_try')
            bounded = await player_service.remove_player(target_user)
            if not bounded:
                return text('core.commands.bound.not_bound_query', target_user=target_user)
            for player in bounded:
                await server_service.execute(f'{config.whitelist_command} remove {player}')
            return text('core.commands.bound.remove_user_all', target_user=target_user)

        async def remove_self_all(self, session: Uninfo):
            """移除当前用户绑定的所有白名单。"""
            player_service, server_service = runtime_state.player_service, runtime_state.server_service
            if player_service is None or server_service is None or not server_service.check_online():
                return text('core.commands.bound.server_offline_try')
            user = str(session.user.id)
            bounded = await player_service.remove_player(user)
            if not bounded:
                return text('core.commands.bound.no_binding_self')
            for player in bounded:
                await server_service.execute(f'{config.whitelist_command} remove {player}')
            return text('core.commands.bound.remove_self_all')

    class Append(SubCommand['BoundCommand']):
        """为指定用户添加绑定。"""

        name = 'append'
        description = i18n_deferred('core.commands.bound.append_desc')

        @override
        def declare(self) -> None:
            self.register_arg('user_id', At | str, description=i18n_deferred('core.commands.bound.arg_user'))
            self.register_arg('player', str, description=i18n_deferred('core.commands.bound.arg_player'))

        @override
        async def handler(self, session: Uninfo, user_id: At | str, player: str):
            if not get_permission(session):
                return text('core.commands.bound.no_permission')
            return await self.append_handler(user_id.target if isinstance(user_id, At) else user_id, player)

        async def append_handler(self, target_user: str, player: str):
            """为指定用户添加玩家绑定。"""
            if not check_player(player):
                return text('core.commands.bound.invalid_name')
            player_service, server_service = runtime_state.player_service, runtime_state.server_service
            if player_service is None:
                return text('core.commands.bound.server_offline')
            if await player_service.check_player_occupied(player):
                return text('core.commands.bound.occupied')
            if server_service is None or not server_service.check_online():
                return text('core.commands.bound.server_offline')
            if await player_service.append_player(target_user, player):
                await server_service.execute(f'{config.whitelist_command} add {player}')
                return text('core.commands.bound.bound_success', name=target_user, user=target_user, player=player)
            return text('core.commands.bound.too_many')
