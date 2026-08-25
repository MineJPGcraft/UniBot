from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse

from Scripts import Globals
from Scripts.Api.Locale import text
from Scripts.Config import config
from Scripts.Managers import cache_manager
from Scripts.Network import AVATAR_SIZE, fetch_player_avatar

from .Auth import get_current_user, require_role
from .Schemas import BindPlayerRequest

router = APIRouter(prefix='/api/players', tags=['Players'])


@router.get('', summary='获取玩家绑定列表')
async def get_players(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(''),
    current_user: dict = Depends(get_current_user),
):
    """获取所有玩家绑定关系，支持搜索和分页。"""
    player_service = Globals.player_service
    bindings = player_service.players if player_service else {}
    all_items = []
    for user_id, bound_players in bindings.items():
        all_items.append({'user': user_id, 'players': bound_players})

    if keyword:
        keyword_lower = keyword.lower()
        all_items = [
            item
            for item in all_items
            if keyword_lower in item['user'].lower()
            or any(keyword_lower in player_name.lower() for player_name in item['players'])
        ]

    total = len(all_items)
    start = (page - 1) * page_size
    items = all_items[start : start + page_size]
    return {
        'code': 0,
        'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size},
        'message': 'ok',
    }


@router.get('/{name}/avatar', summary='获取玩家头像')
async def get_player_avatar(
    name: str,
    size: int = Query(24, ge=8, le=128),
    current_user: dict = Depends(get_current_user),
):
    """获取玩家头像：本地缓存优先，缺失时下载并落盘缓存，避免重复请求外部 CDN。"""
    cached, _ = cache_manager.get_cached([name])
    if name in cached:
        return FileResponse(cached[name], media_type='image/png')
    result = await fetch_player_avatar(name, size)
    if result is None:
        return Response(status_code=404)
    content, content_type = result
    # 与缓存尺寸一致时顺手落盘，供 List 渲染等复用
    if size == AVATAR_SIZE:
        await cache_manager.save_all({cache_manager.get_path(name).name: content})
    return Response(content=content, media_type=content_type)


@router.get('/{user}', summary='查询用户绑定')
async def get_user_bindings(user: str, current_user: dict = Depends(get_current_user)):
    """查询指定用户的所有绑定。"""
    player_service = Globals.player_service
    bindings = player_service.players if player_service else {}
    if user not in bindings:
        return {'code': 1, 'data': None, 'message': text('players.user_not_found')}
    return {'code': 0, 'data': {'user': user, 'players': bindings[user]}, 'message': 'ok'}


@router.post('', summary='绑定玩家')
async def bind_player(body: BindPlayerRequest, current_user: dict = Depends(require_role('admin', 'operator'))):
    """绑定用户与游戏 ID。"""
    if not body.user or not body.player:
        return {'code': 1, 'data': None, 'message': text('players.bind_fields_required')}

    player_service = Globals.player_service
    if player_service is None:
        return {'code': 1, 'data': None, 'message': text('players.service_unavailable')}

    # 检查该游戏 ID 是否已被其他用户绑定
    if await player_service.check_player_occupied(body.player):
        existing_user = next(
            (
                bound_user
                for bound_user, bound_players in player_service.players.items()
                if body.player.lower() in [p.lower() for p in bound_players]
            ),
            None,
        )
        if existing_user and existing_user != body.user:
            return {'code': 1, 'data': None, 'message': text('players.bound_by_other_user')}

    if (
        body.user in player_service.players
        and config.qq_bound_max_number > 0
        and len(player_service.players[body.user]) >= config.qq_bound_max_number
    ):
        return {'code': 1, 'data': None, 'message': text('players.bind_limit_reached')}

    success = await player_service.append_player(body.user, body.player)
    if not success:
        return {'code': 1, 'data': None, 'message': text('players.bind_limit_reached')}
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.delete('/{user}/{player}', summary='解除绑定')
async def unbind_player(user: str, player: str, current_user: dict = Depends(require_role('admin', 'operator'))):
    """解除用户与游戏 ID 的绑定。"""
    player_service = Globals.player_service
    bindings = player_service.players if player_service else {}
    if user not in bindings or player not in bindings.get(user, []):
        return {'code': 1, 'data': None, 'message': text('players.binding_not_found')}
    await player_service.remove_player(user, player)
    return {'code': 0, 'data': None, 'message': 'ok'}
