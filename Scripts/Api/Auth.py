import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from Scripts.Api.Managers import data_manager
from Scripts.Logging import logger

from .Limiter import rate_limiter
from .Schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SetupRequest,
    UpdateProfileRequest,
)

# Cookie 配置
COOKIE_ACCESS_KEY = 'unibot_access_token'
COOKIE_REFRESH_KEY = 'unibot_refresh_token'
COOKIE_FLAG_KEY = 'unibot_authenticated'

ACCESS_TOKEN_EXPIRE_HOURS = 2
REFRESH_TOKEN_EXPIRE_DAYS = 7


def set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str | None = None):
    """设置 HttpOnly 安全 cookie（access_token 短期 + refresh_token 长期）。"""
    response.set_cookie(
        key=COOKIE_ACCESS_KEY,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        httponly=True,
        samesite='lax',
        # secure=True,   # 生产环境开启（需 HTTPS）
        path='/webui',
    )
    if refresh_token:
        response.set_cookie(
            key=COOKIE_REFRESH_KEY,
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            httponly=True,
            samesite='lax',
            # secure=True,
            path='/webui',
        )
    # 非 HttpOnly 标记 cookie，仅用于前端快速判断登录态，不含敏感信息
    response.set_cookie(
        key=COOKIE_FLAG_KEY,
        value='1',
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=False,
        samesite='lax',
        path='/webui',
    )


def clear_auth_cookies(response: JSONResponse):
    """清除所有认证 cookie（以 max_age=0 重新下发同名 cookie 实现删除）。"""
    for key in (COOKIE_ACCESS_KEY, COOKIE_REFRESH_KEY, COOKIE_FLAG_KEY):
        response.delete_cookie(key=key, path='/webui')


router = APIRouter(
    prefix='/api/auth',
    tags=['Auth'],
    dependencies=[Depends(rate_limiter.check)],
)

# 初始化接口并发锁：防止「检测无用户 → 创建用户」之间被并发请求插入
setup_lock = asyncio.Lock()

# 哑密码哈希：用户不存在时仍执行一次 bcrypt 校验，抹平响应时延差防用户名枚举
DUMMY_PASSWORD_HASH = bcrypt.hashpw(uuid.uuid4().hex.encode('Utf-8'), bcrypt.gensalt()).decode('Utf-8')


def refresh_token_expire_at(token: str) -> float:
    """解析 refresh_token 的过期时间戳，无效令牌返回 0。"""
    try:
        payload = jwt.decode(token, data_manager.secret_key, algorithms=['HS256'], options={'verify_exp': False})
    except jwt.InvalidTokenError:
        return 0.0
    return float(payload.get('exp') or 0)


def create_access_token(user_id: str, role: str) -> str:
    """签发 access_token。"""
    payload = {
        'sub': user_id,
        'role': role,
        'type': 'access',
        'exp': datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, data_manager.secret_key, algorithm='HS256')


def create_refresh_token(user_id: str) -> str:
    """签发 refresh_token。"""
    payload = {
        'sub': user_id,
        'type': 'refresh',
        'exp': datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, data_manager.secret_key, algorithm='HS256')


async def get_current_user(request: Request, authorization: str | None = Header(None)) -> dict:
    """解析 JWT，返回当前用户对象（优先从 Authorization header，fallback 到 cookie）。"""
    token = None
    if authorization and authorization.startswith('Bearer '):
        token = authorization[7:]
    if not token:
        token = request.cookies.get(COOKIE_ACCESS_KEY)
    if not token:
        raise HTTPException(status_code=401, detail='未认证')
    try:
        payload = jwt.decode(token, data_manager.secret_key, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token 已过期')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='无效的 Token')
    if payload.get('type') != 'access':
        raise HTTPException(status_code=401, detail='无效的 Token 类型')
    user_data = data_manager.get_user_by_id(payload['sub'])
    if not user_data:
        raise HTTPException(status_code=401, detail='用户不存在')
    return user_data


def require_role(*roles: str):
    """角色校验依赖工厂。"""

    async def checker(user: dict = Depends(get_current_user)):
        if user['role'] not in roles:
            raise HTTPException(status_code=403, detail='权限不足')
        return user

    return checker


def decode_access_token_payload(token: str) -> dict | None:
    """校验 access_token 并返回 payload，无效或类型不符时返回 None。"""
    try:
        payload = jwt.decode(token, data_manager.secret_key, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return None
    if payload.get('type') != 'access':
        return None
    return payload


@router.get('/status', summary='获取认证状态')
async def auth_status():
    """返回系统是否已初始化（无需认证），供登录页决定是否展示初始化入口。"""
    return {'code': 0, 'data': {'initialized': data_manager.is_initialized}, 'message': 'ok'}


@router.post('/setup', summary='首次初始化')
async def setup(body: SetupRequest):
    """首次初始化：创建管理员账户，仅在无任何用户时可用。"""
    async with setup_lock:
        if data_manager.is_initialized:
            return {'code': 1, 'data': None, 'message': '系统已初始化，禁止重复创建管理员账户'}
        user_info = await data_manager.create_user(body.username, body.password, body.nickname, role='admin')
        if user_info is None:
            return {'code': 1, 'data': None, 'message': '创建失败！'}
    logger.success(f'WebUI admin account [{body.username}] created.')
    return {'code': 0, 'data': {'user_id': user_info['user_id']}, 'message': '初始化成功'}


@router.post('/login', summary='用户登录')
async def login(body: LoginRequest):
    """用户名密码登录，通过 HttpOnly cookie 下发 JWT。"""
    user_data = data_manager.get_user_by_username(body.username)
    # 未知用户也走一次哑校验，避免响应时延差异暴露用户名是否存在
    password_hash = user_data['password_hash'] if user_data else DUMMY_PASSWORD_HASH
    if not await data_manager.verify_password(body.password, password_hash):
        return {'code': 1, 'data': None, 'message': '用户名或密码错误'}
    assert user_data is not None  # 上面已校验过
    await data_manager.update_last_login(user_data['user_id'])
    access_token = create_access_token(user_data['user_id'], user_data['role'])
    refresh_token = create_refresh_token(user_data['user_id'])
    response = JSONResponse(
        {
            'code': 0,
            'data': {
                'user': data_manager.public_user_info(user_data),
                'expires_in': ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            },
            'message': 'ok',
        }
    )
    set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post('/refresh', summary='刷新 Token')
async def refresh(request: Request, body: RefreshRequest):
    """使用 refresh_token 换取新的 access_token（优先从 cookie 读取）。"""
    refresh_token = request.cookies.get(COOKIE_REFRESH_KEY) or body.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=401, detail='缺少 refresh_token')
    if data_manager.is_refresh_token_revoked(refresh_token):
        raise HTTPException(status_code=401, detail='Token 已失效')
    try:
        payload = jwt.decode(refresh_token, data_manager.secret_key, algorithms=['HS256'])
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=401, detail='无效的 refresh_token') from error
    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='无效的 Token 类型')
    user_data = data_manager.get_user_by_id(payload['sub'])
    if not user_data:
        raise HTTPException(status_code=401, detail='用户不存在')
    access_token = create_access_token(user_data['user_id'], user_data['role'])
    response = JSONResponse(
        {
            'code': 0,
            'data': {'expires_in': ACCESS_TOKEN_EXPIRE_HOURS * 3600},
            'message': 'ok',
        }
    )
    set_auth_cookies(response, access_token)  # 刷新 access_token cookie
    return response


@router.post('/logout', summary='退出登录')
async def logout(request: Request, body: LogoutRequest | None = None):
    """使当前 refresh_token 失效并清除 cookie（无论请求体或 cookie 是否存在）。"""
    refresh_token = request.cookies.get(COOKIE_REFRESH_KEY) or (body.refresh_token if body else '')
    if refresh_token:
        await data_manager.revoke_refresh_token(refresh_token, refresh_token_expire_at(refresh_token))
    response = JSONResponse({'code': 0, 'data': None, 'message': 'ok'})
    clear_auth_cookies(response)
    return response


@router.get('/me', summary='获取当前用户信息')
async def get_me(user: dict = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return {'code': 0, 'data': data_manager.public_user_info(user), 'message': 'ok'}


@router.put('/password', summary='修改密码')
async def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """修改当前用户密码。"""
    if not await data_manager.verify_password(body.old_password, user['password_hash']):
        return {'code': 1, 'data': None, 'message': '原密码错误'}
    await data_manager.reset_password(user['user_id'], body.new_password)
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.put('/profile', summary='修改昵称')
async def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """修改当前用户昵称。"""
    await data_manager.update_user(user['user_id'], nickname=body.nickname)
    return {'code': 0, 'data': None, 'message': 'ok'}
