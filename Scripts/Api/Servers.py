import asyncio

from fastapi import APIRouter, Depends

from Scripts import Globals
from Scripts.Config import config
from Scripts.Logging import logger
from Scripts.Utils import strip_minecraft_color

from .Auth import get_current_user, require_role
from .Schemas import BroadcastRequest, ExecuteCommandRequest

router = APIRouter(prefix='/api/servers', tags=['Servers'])


def check_command_allowed(command: str) -> bool:
    """检查指令是否在白名单/黑名单约束内。"""
    command_name = command.strip().split()[0].lower() if command.strip() else ''
    if config.command_minecraft_whitelist:
        return command_name in [item.lower() for item in config.command_minecraft_whitelist]
    if config.command_minecraft_blacklist:
        return command_name not in [item.lower() for item in config.command_minecraft_blacklist]
    return True


@router.get('', summary='获取服务器列表')
async def get_servers(current_user: dict = Depends(get_current_user)):
    """获取所有服务器状态。"""
    server_service = Globals.server_service
    if server_service is None:
        return {'code': 1, 'data': [], 'message': 'Minecraft 服务器服务不可用'}
    servers = server_service.servers
    statuses = await asyncio.gather(*(server_service.get_status(server) for server in servers.values()))
    server_list = [{'name': name, **status} for name, status in zip(servers, statuses)]
    return {'code': 0, 'data': server_list, 'message': 'ok'}


@router.get('/{name}', summary='获取服务器详情')
async def get_server_detail(name: str, current_user: dict = Depends(get_current_user)):
    """获取单个服务器详情。"""
    server_service = Globals.server_service
    if server_service is None:
        return {'code': 1, 'data': None, 'message': 'Minecraft 服务器服务不可用'}
    servers = server_service.servers
    if name not in servers:
        return {'code': 1, 'data': None, 'message': f'服务器 [{name}] 不存在'}
    status, player_data = await asyncio.gather(
        server_service.get_status(servers[name]),
        server_service.get_player_list(servers[name]),
    )
    players, max_players = player_data
    if not status['max_players']:
        status['max_players'] = max_players
    status['players'] = len(players)
    return {
        'code': 0,
        'data': {
            'name': name,
            **status,
            'player_list': players,
        },
        'message': 'ok',
    }


@router.get('/{name}/players', summary='获取服务器在线玩家')
async def get_server_players(name: str, current_user: dict = Depends(get_current_user)):
    """获取指定服务器的在线玩家列表。"""
    server_service = Globals.server_service
    if server_service is None:
        return {'code': 1, 'data': None, 'message': 'Minecraft 服务器服务不可用'}
    servers = server_service.servers
    if name not in servers:
        return {'code': 1, 'data': None, 'message': f'服务器 [{name}] 不存在'}
    players, max_players = await server_service.get_player_list(servers[name])
    return {
        'code': 0,
        'data': {'server': name, 'players': players, 'count': len(players), 'max_players': max_players},
        'message': 'ok',
    }


@router.post('/{name}/execute', summary='执行 RCON 指令')
async def execute_command(
    name: str, body: ExecuteCommandRequest, current_user: dict = Depends(require_role('admin', 'operator'))
):
    """在指定服务器执行 RCON 指令，name 为 all 时广播。"""
    if not body.command:
        return {'code': 1, 'data': None, 'message': '指令不能为空'}
    if not check_command_allowed(body.command):
        return {'code': 1, 'data': None, 'message': '该指令不在允许范围内'}

    server_service = Globals.server_service
    if server_service is None:
        return {'code': 1, 'data': None, 'message': 'Minecraft 服务器服务不可用'}

    if name == 'all':
        results = await server_service.execute(body.command)
        return {'code': 0, 'data': results or {}, 'message': 'ok'}

    bot = server_service.get_server(name)
    if bot is None:
        return {'code': 1, 'data': None, 'message': f'服务器 [{name}] 不存在'}

    try:
        result = await bot.send_rcon_command(command=body.command)
    except Exception as error:
        logger.warning(f'Failed to send command to server [{name}]: {error}')
        return {'code': 1, 'data': None, 'message': f'指令执行失败：{error}'}
    response_text = strip_minecraft_color(result) if result else ''
    return {'code': 0, 'data': {'response': response_text}, 'message': 'ok'}


@router.post('/broadcast', summary='广播消息')
async def broadcast_message(body: BroadcastRequest, current_user: dict = Depends(require_role('admin', 'operator'))):
    """广播消息到所有服务器。"""
    if not body.message:
        return {'code': 1, 'data': None, 'message': '消息不能为空'}
    server_service = Globals.server_service
    if server_service is None:
        return {'code': 1, 'data': None, 'message': 'Minecraft 服务器服务不可用'}
    await server_service.broadcast(body.message)
    logger.info(f'WebUI broadcast message: {body.message}')
    return {'code': 0, 'data': None, 'message': 'ok'}
