import asyncio
from datetime import datetime

from nonebot import on_message, on_notice
from nonebot.adapters.minecraft import (
    PlayerAchievementEvent,
    PlayerChatEvent,
    PlayerDeathEvent,
    PlayerJoinEvent,
    PlayerQuitEvent,
)
from nonebot.adapters.minecraft.message import MessageSegment
from nonebot.adapters.minecraft.models import Component, HoverAction, HoverEvent
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna.uniseg import UniMsg
from nonebot_plugin_uninfo import Uninfo

from Scripts import Globals
from Scripts.Config import config
from Scripts.Logging import logger
from Scripts.Messages import messages as message_config
from Scripts.Rules import message_group_rule
from Scripts.Utils import check_message, get_platform_name, send_message_to_groups

__plugin_meta__ = PluginMetadata(
    name='消息互通',
    description='处理玩家事件以及聊天平台与 Minecraft 服务器之间的消息同步。',
    usage='由相关消息与服务器事件自动触发。',
)

# 玩家聊天中触发「转发到群聊」的指令前缀
CHAT_COMMAND_PREFIXES = ('send', 'gp', 'qq', 'q')

notice_watcher = on_notice()
player_chat_watcher = on_message()
message_watcher = on_message(rule=message_group_rule)

# 持有后台广播任务引用，防止任务被垃圾回收
_background_tasks: set[asyncio.Task] = set()

segment_mapping = {
    'text': lambda segment: segment.text,
    'at': lambda segment: f'[@{segment.target}]',
    'reply': lambda segment: f'[引用{"：" + segment.msg.extract_plain_text() if segment.msg else ""}]',
    'reference': lambda _: '[引用消息]',
    'atall': lambda _: '[@全体成员]',
    'emoji': lambda _: '[动画表情]',
    'image': lambda _: '[图片]',
    'video': lambda _: '[视频]',
    'audio': lambda _: '[语音]',
    'file': lambda _: '[文件]',
}


def message_to_text(message: UniMsg):
    """将 UniMsg 转换为文本。"""
    texts = [res for segment in message if (func := segment_mapping.get(segment.type)) and (res := func(segment))]
    return ' '.join(texts)


def build_server_message(source: str, player: str, content: str):
    """构建服务器消息。"""
    now_time = datetime.now().strftime('%H:%M:%S')
    hover_event = HoverEvent(action=HoverAction.show_text, contents=Component(text=now_time))
    message = MessageSegment.text(f'[{source}] ', color=config.sync_color_source, hover_event=hover_event)
    message += MessageSegment.text(f'[{player}] ', color=config.sync_color_player, hover_event=hover_event)
    message += MessageSegment.text(content, color=config.sync_color_message, hover_event=hover_event)
    return message


async def broadcast_to_servers(server_name: str, player: str, content: str) -> None:
    """向除来源服务器外的所有已连接服务器同步消息（未开启同步或无服务时跳过）。"""
    if not config.sync_message_between_servers:
        return
    server_service = Globals.server_service
    if server_service is None:
        return
    await server_service.broadcast(build_server_message(server_name, player, content), server_name)


@notice_watcher.handle()
async def handle_player_join(event: PlayerJoinEvent):
    """处理玩家加入服务器事件。"""
    name = event.server_name
    player = event.player.nickname
    logger.info(f'Player {player} joined server [{name}].')

    if config.list_compatible_mode:
        if name not in Globals.player_list_cache:
            Globals.player_list_cache[name] = []
        if (
            not config.bot_prefix or not player.upper().startswith(config.bot_prefix)
        ) and player not in Globals.player_list_cache[name]:
            Globals.player_list_cache[name].append(player)

    server_message = message_config.events.player_join.format(player=player)
    group_message = message_config.events.player_join_group.format(player=player, server=name)

    if config.bot_prefix and player.upper().startswith(config.bot_prefix):
        group_message = message_config.events.fake_join_group.format(player=player, server=name)
        server_message = message_config.events.fake_join_game.format(server=name, player=player)

    await broadcast_to_servers(name, player, server_message)

    if config.broadcast_player:
        await send_message_to_groups(group_message)


@notice_watcher.handle()
async def handle_player_quit(event: PlayerQuitEvent):
    """处理玩家离开服务器事件。"""
    name = event.server_name
    player = event.player.nickname
    logger.info(f'Player {player} left server [{name}].')

    if config.list_compatible_mode and name in Globals.player_list_cache and player in Globals.player_list_cache[name]:
        Globals.player_list_cache[name].remove(player)

    server_message = message_config.events.player_quit.format(player=player)
    group_message = message_config.events.player_quit_group.format(player=player, server=name)

    if config.bot_prefix and player.upper().startswith(config.bot_prefix):
        server_message = message_config.events.fake_quit_game.format(player=player)
        group_message = message_config.events.fake_quit_group.format(player=player, server=name)

    await broadcast_to_servers(name, player, server_message)

    if config.broadcast_player:
        await send_message_to_groups(group_message)


@notice_watcher.handle()
async def handle_player_death(event: PlayerDeathEvent):
    """处理玩家死亡事件。"""
    name = event.server_name
    player = event.player.nickname
    death_message = event.death.text or f'{player} 死亡了'
    logger.debug(f'Player death message received: {death_message}')

    if (not config.bot_prefix) or (not player.upper().startswith(config.bot_prefix)):
        broadcast_message = message_config.events.player_death.format(player=player, death=death_message)
        await broadcast_to_servers(name, player, broadcast_message)
        if config.broadcast_player:
            await send_message_to_groups(broadcast_message)


@notice_watcher.handle()
async def handle_player_achievement(event: PlayerAchievementEvent):
    """处理玩家达成成就事件。"""
    name = event.server_name
    player = event.player.nickname
    achievement = event.achievement

    if achievement.translate and achievement.translate.text:
        achievement_message = achievement.translate.text
    elif achievement.display and achievement.display.title and achievement.display.title.text:
        achievement_message = f'{player} 达成了成就 [{achievement.display.title.text}]'
    else:
        achievement_message = f'{player} 达成了成就 [{achievement.key or "未知成就"}]'
    logger.debug(f'Player achievement message received: {achievement_message}')

    if (not config.bot_prefix) or (not player.upper().startswith(config.bot_prefix)):
        broadcast_message = message_config.events.player_achievement.format(
            player=player, achievement=achievement_message
        )
        await broadcast_to_servers(name, player, broadcast_message)
        if config.broadcast_player:
            await send_message_to_groups(broadcast_message)


@player_chat_watcher.handle()
async def handle_player_chat(event: PlayerChatEvent):
    """处理玩家聊天事件。"""
    name = event.server_name
    player = event.player.nickname
    chat_message = event.message.extract_plain_text().strip()
    logger.debug(f'Player {player} sent a message on server [{name}].')

    if config.sync_message_between_servers:
        server_service = Globals.server_service
        if server_service is not None:
            # 后台广播不阻塞聊天转发；持引用防止任务被 GC
            message = build_server_message(name, player, chat_message)
            broadcast_task = asyncio.create_task(server_service.broadcast(message, name))
            _background_tasks.add(broadcast_task)
            broadcast_task.add_done_callback(_background_tasks.discard)

    if config.sync_all_game_message:
        if check_message(chat_message):
            logger.warning(f'Message {chat_message} contains sensitive words, discarded.')
            return

        await send_message_to_groups(
            message_config.events.chat_forward.format(server=name, player=player, content=chat_message)
        )
        return

    logger.debug(f'Server message received: {chat_message}')
    if ' ' not in chat_message:
        return
    start, content = chat_message.split(' ', maxsplit=1)
    if start.lower() not in CHAT_COMMAND_PREFIXES:
        return
    server_service = Globals.server_service
    server = server_service.get_server(name) if server_service else None
    if server is None:
        return
    if not content:
        message = MessageSegment.text(message_config.events.need_content, color='red')
        await server.send_private_msg(message=message, nickname=player)
        return
    if check_message(content):
        message = MessageSegment.text(message_config.events.sensitive_reply, color='red')
        await server.send_private_msg(message=message, nickname=player)
        return
    await send_message_to_groups(message_config.events.chat_forward.format(server=name, player=player, content=content))
    message = MessageSegment.text(message_config.events.sent_success, color='green')
    await server.send_private_msg(message=message, nickname=player)


@message_watcher.handle()
async def handle_group_message(message: UniMsg, session: Uninfo):
    platform_name = get_platform_name(session.scope)
    plain_text_message = message.extract_plain_text()
    if any(plain_text_message.startswith(prefix) for prefix in config.command_start):
        return
    player_service, server_service = Globals.player_service, Globals.server_service
    user_name = player_service.players.get(str(session.user.id), (None,))[0] if player_service else None
    user_name = user_name or session.user.nick or session.user.name or str(session.user.id)
    if server_service is not None:
        await server_service.broadcast(build_server_message(platform_name, user_name, message_to_text(message)))
