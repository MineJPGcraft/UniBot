from fastapi import APIRouter, Depends, Query

from Scripts.Api.Managers import data_manager

from .Auth import require_role
from .Schemas import CreateUserRequest, ResetPasswordRequest, UpdateUserRequest

router = APIRouter(prefix='/api/users', tags=['Users'], dependencies=[Depends(require_role('admin'))])


@router.get('', summary='获取用户列表')
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(''),
    current_user: dict = Depends(require_role('admin')),
):
    """分页获取用户列表。"""
    all_users = [data_manager.public_user_info(user_info) for user_info in data_manager.users.values()]
    if keyword:
        keyword_lower = keyword.lower()
        all_users = [
            user_info
            for user_info in all_users
            if keyword_lower in user_info['username'].lower() or keyword_lower in user_info['nickname'].lower()
        ]
    total = len(all_users)
    start = (page - 1) * page_size
    items = all_users[start : start + page_size]
    return {
        'code': 0,
        'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size},
        'message': 'ok',
    }


@router.post('', summary='创建用户')
async def create_user(body: CreateUserRequest, current_user: dict = Depends(require_role('admin'))):
    """创建新用户。"""
    if body.role not in ('admin', 'operator', 'viewer'):
        return {'code': 1, 'data': None, 'message': '无效的角色'}
    user_info = await data_manager.create_user(body.username, body.password, body.nickname, body.role)
    if not user_info:
        return {'code': 1, 'data': None, 'message': '用户名已存在'}
    return {'code': 0, 'data': {'user_id': user_info['user_id']}, 'message': 'ok'}


@router.get('/{user_id}', summary='获取用户详情')
async def get_user(user_id: str, current_user: dict = Depends(require_role('admin'))):
    """获取指定用户详情。"""
    user_data = data_manager.get_user_by_id(user_id)
    if not user_data:
        return {'code': 1, 'data': None, 'message': '用户不存在'}
    return {'code': 0, 'data': data_manager.public_user_info(user_data), 'message': 'ok'}


@router.put('/{user_id}', summary='修改用户信息')
async def update_user(user_id: str, body: UpdateUserRequest, current_user: dict = Depends(require_role('admin'))):
    """修改用户昵称或角色，不可修改自己的角色。"""
    if user_id == current_user['user_id'] and body.role is not None:
        return {'code': 1, 'data': None, 'message': '不可修改自己的角色'}
    if body.role is not None and body.role not in ('admin', 'operator', 'viewer'):
        return {'code': 1, 'data': None, 'message': '无效的角色'}
    success = await data_manager.update_user(user_id, nickname=body.nickname, role=body.role)
    if not success:
        return {'code': 1, 'data': None, 'message': '用户不存在'}
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.put('/{user_id}/password', summary='重置用户密码')
async def reset_user_password(
    user_id: str, body: ResetPasswordRequest, current_user: dict = Depends(require_role('admin'))
):
    """重置指定用户密码。"""
    success = await data_manager.reset_password(user_id, body.password)
    if not success:
        return {'code': 1, 'data': None, 'message': '用户不存在'}
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.delete('/{user_id}', summary='删除用户')
async def delete_user(user_id: str, current_user: dict = Depends(require_role('admin'))):
    """删除用户，不可删除自己。"""
    if user_id == current_user['user_id']:
        return {'code': 1, 'data': None, 'message': '不可删除自己'}
    success = await data_manager.delete_user(user_id)
    if not success:
        return {'code': 1, 'data': None, 'message': '用户不存在'}
    return {'code': 0, 'data': None, 'message': 'ok'}
