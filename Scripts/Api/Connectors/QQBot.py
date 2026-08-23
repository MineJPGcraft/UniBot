"""
QQ 官方机器人扫码绑定 API。

将 `Scripts/Connectors/QQOfficial` 的扫码流程封装为 WebUI 可调用的接口：
  - POST   /api/connectors/qq/qr/login          启动扫码登录（返回二维码图片）
  - GET    /api/connectors/qq/qr/login/stream   扫码登录 SSE 流（启动 + 推送状态）
  - GET    /api/connectors/qq/qr/login          查询当前登录状态
  - DELETE /api/connectors/qq/qr/login          取消当前登录
"""

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from Scripts.Connectors.QQOfficial import (
    cancel_qr_login,
    get_qr_login,
    qr_login,
    start_qr_login,
)

from ..Auth import require_role

router = APIRouter(prefix='/api/connectors/qq', tags=['Connectors/QQ'])


class StartQrLoginRequest(BaseModel):
    """启动扫码登录的请求体。"""

    source: str = ''  # 接入平台标识，会拼到二维码 URL 中
    env: str = 'production'  # "production" 或 "test"


@router.post('/qr/login', summary='启动 QQ 扫码登录')
async def start_login(
    body: StartQrLoginRequest,
    user: dict = Depends(require_role('admin')),
):
    """启动扫码登录并返回二维码图片（data URL），前端展示后轮询状态。"""
    try:
        state = start_qr_login(source=body.source, env=body.env)
    except Exception as error:
        return {'code': 1, 'data': None, 'message': f'启动扫码登录失败：{error}'}
    return {'code': 0, 'data': state.to_dict(), 'message': 'ok'}


@router.get(
    '/qr/login/stream',
    summary='QQ 扫码登录 SSE 流',
    response_class=EventSourceResponse,
)
async def stream_login(
    request: Request,
    source: str = '',
    env: str = 'production',
    user: dict = Depends(require_role('admin')),
) -> AsyncIterator[ServerSentEvent]:
    """
    启动扫码登录并通过 SSE 推送状态变化。

    前端用 `EventSource` 打开本端点即启动登录，每次状态变化推送一个
    `QrLoginState`（JSON）。连接断开时自动取消登录流程。
    """
    # 同一时刻只允许一个扫码登录，先取消旧的
    cancel_qr_login()
    cancel_event = asyncio.Event()
    try:
        async for state in qr_login(
            source=source,
            env=env,
            cancel_event=cancel_event,
        ):
            if await request.is_disconnected():
                cancel_event.set()
                break
            yield ServerSentEvent(data=state.to_dict(), event='qr')
    finally:
        cancel_event.set()


@router.get('/qr/login', summary='查询当前扫码登录状态')
async def get_login(user: dict = Depends(require_role('admin'))):
    """轮询当前扫码登录状态；完成时返回 app_id / app_secret 凭据。"""
    state = get_qr_login()
    if state is None:
        return {'code': 1, 'data': None, 'message': '当前没有进行中的扫码登录'}
    return {'code': 0, 'data': state.to_dict(), 'message': 'ok'}


@router.delete('/qr/login', summary='取消当前扫码登录')
async def cancel_login(user: dict = Depends(require_role('admin'))):
    """取消当前扫码登录并停止后台轮询。"""
    cancelled = cancel_qr_login()
    if not cancelled:
        return {'code': 1, 'data': None, 'message': '当前没有进行中的扫码登录'}
    return {'code': 0, 'data': None, 'message': 'ok'}
