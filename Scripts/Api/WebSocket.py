import asyncio
from datetime import datetime

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from Scripts.Logging import logger
from Scripts.Managers import data_manager

router = APIRouter(tags=['WebSocket'])

# 已连接的 WebSocket 客户端及其订阅的事件
ws_clients: dict[WebSocket, set[str]] = {}

# 运行状态推送间隔（秒）
STATUS_PUSH_INTERVAL = 3

# 最近推送的日志缓存，新客户端订阅时补发（避免漏掉连接前的日志）
LOG_CACHE_SIZE = 50
log_cache: list[dict] = []
log_seq_counter = 0


async def broadcast_event(event_type: str, data: dict):
    """向所有订阅了该事件的 WebSocket 客户端推送消息。"""
    message = {'type': event_type, 'data': data}
    disconnected = []
    for websocket, subscribed_events in ws_clients.items():
        if event_type in subscribed_events:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
    for websocket in disconnected:
        ws_clients.pop(websocket, None)


def log_sink(message):
    """loguru sink，将日志推送到 WebSocket 客户端并写入缓存。"""
    global log_seq_counter
    record = message.record
    log_seq_counter += 1
    log_data = {
        'seq': log_seq_counter,
        'level': record['level'].name,
        # 与历史日志文件中的时间格式保持一致（HH:MM:SS.mmm），保证前端各列对齐
        'time': datetime.fromtimestamp(record['time'].timestamp()).strftime('%H:%M:%S.%f')[:-3],
        'message': record['message'],
        'module': record['name'],
        # 完整 ANSI 彩色行（含级别/模块名/消息内着色），前端解析渲染
        'ansi': str(message),
    }
    log_cache.append(log_data)
    if len(log_cache) > LOG_CACHE_SIZE:
        del log_cache[0]
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcast_event('log', log_data))
    except RuntimeError:
        pass


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点，支持订阅日志、服务器、玩家、系统事件。"""
    # 通过 cookie 中的 access_token 验证身份（fallback 到 query 参数兼容旧版）
    token = websocket.cookies.get('unibot_access_token', '') or websocket.query_params.get('token', '')
    if not token:
        await websocket.close(code=4001, reason='Unauthorized')
        return
    try:
        payload = jwt.decode(token, data_manager.secret_key, algorithms=['HS256'])
        if payload.get('type') != 'access':
            raise jwt.InvalidTokenError()
    except jwt.InvalidTokenError:
        await websocket.close(code=4001, reason='Unauthorized')
        return

    await websocket.accept()
    ws_clients[websocket] = set()
    logger.debug('WebUI WebSocket client connected.')

    async def status_pusher():
        """定期向订阅了 status 事件的当前客户端推送运行状态。"""
        from .Status import get_status_data  # 延迟导入避免循环依赖

        while True:
            await asyncio.sleep(STATUS_PUSH_INTERVAL)
            if 'status' not in ws_clients.get(websocket, set()):
                continue
            try:
                await websocket.send_json({'type': 'status', 'data': get_status_data()})
            except Exception:
                break

    push_task = asyncio.create_task(status_pusher())

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get('type', '')

            if message_type == 'subscribe':
                events = data.get('events', [])
                ws_clients[websocket] = set(events)
                await websocket.send_json({'type': 'subscribed', 'events': list(ws_clients[websocket])})
                # 订阅日志后补发缓存的最近日志，供前端初始化实时日志列表
                if 'log' in ws_clients[websocket] and log_cache:
                    await websocket.send_json({'type': 'log_history', 'data': list(log_cache)})

            elif message_type == 'unsubscribe':
                events = data.get('events', [])
                ws_clients[websocket] -= set(events)
                await websocket.send_json({'type': 'subscribed', 'events': list(ws_clients[websocket])})

            elif message_type == 'ping':
                await websocket.send_json({'type': 'pong'})

    except WebSocketDisconnect:
        logger.debug('WebUI WebSocket client disconnected.')
    except Exception as error:
        logger.warning(f'WebSocket error: {error}')
    finally:
        push_task.cancel()
        ws_clients.pop(websocket, None)
