import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from Core.Logging import logger

from .Auth import COOKIE_ACCESS_KEY, decode_access_token_payload

router = APIRouter(tags=['WebSocket'])

# 已连接的 WebSocket 客户端及其订阅的事件
ws_clients: dict[WebSocket, set[str]] = {}

# 是否允许通过 URL query 参数携带 token 认证（默认禁用）。
# URL 会进入浏览器历史、代理与访问日志，仅在确有跨源受限客户端需求时才启用。
ALLOW_QUERY_TOKEN = False

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
    # 快照连接表：await 期间允许其它连接增删成员，避免字典迭代期变更
    for websocket, subscribed_events in tuple(ws_clients.items()):
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
        # 完整 ANSI 彩色行（含级别/模块名/消息内着色），前端解析渲染；
        # 去掉格式模板自带的尾部换行，避免前端 pre-wrap 渲染出空行
        'ansi': str(message).rstrip('\n'),
    }
    log_cache.append(log_data)
    if len(log_cache) > LOG_CACHE_SIZE:
        del log_cache[0]
    # 仅在事件循环线程内时推送；跨线程调用（无运行中的循环）直接跳过
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_event('log', log_data))


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点，支持订阅日志、服务器、玩家、系统事件。"""
    if not await _authenticate_websocket(websocket):
        return

    await websocket.accept()
    ws_clients[websocket] = set()
    logger.debug('WebUI WebSocket client connected.')

    push_task = asyncio.create_task(_status_pusher(websocket))
    try:
        await _pump_messages(websocket)
    except WebSocketDisconnect:
        logger.debug('WebUI WebSocket client disconnected.')
    except Exception as error:
        logger.warning(f'WebSocket error: {error}')
    finally:
        push_task.cancel()
        ws_clients.pop(websocket, None)


async def _authenticate_websocket(websocket: WebSocket) -> bool:
    """校验 WebSocket 身份，失败即关闭连接并返回 `False`。"""
    # 仅接受同源 HttpOnly cookie（浏览器 WebSocket 自动携带）。
    # query 参数中的 token 会进入浏览器历史、代理与访问日志，默认禁用；
    # 仅当部署确有跨源受限客户端需求时，才将 ALLOW_QUERY_TOKEN 显式置为 True。
    token = websocket.cookies.get(COOKIE_ACCESS_KEY, '')
    if not token and ALLOW_QUERY_TOKEN:
        logger.warning('WebSocket query token fallback is enabled; tokens may leak via logs.')
        token = websocket.query_params.get('token', '')
    if decode_access_token_payload(token):
        return True
    await websocket.close(code=4001, reason='Unauthorized')
    return False


async def _status_pusher(websocket: WebSocket) -> None:
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


async def _pump_messages(websocket: WebSocket) -> None:
    """循环接收并分发客户端消息，直至断开。"""
    while True:
        data = await websocket.receive_json()
        message_type = data.get('type', '')
        if message_type == 'subscribe':
            await _handle_subscribe(websocket, data.get('events', []))
        elif message_type == 'unsubscribe':
            await _handle_unsubscribe(websocket, data.get('events', []))
        elif message_type == 'ping':
            await websocket.send_json({'type': 'pong'})


async def _handle_subscribe(websocket: WebSocket, events: list) -> None:
    """处理订阅请求，并在订阅日志后补发缓存日志。"""
    ws_clients[websocket] = set(events)
    await websocket.send_json({'type': 'subscribed', 'events': list(ws_clients[websocket])})
    # 订阅日志后补发缓存的最近日志，供前端初始化实时日志列表
    if 'log' in ws_clients[websocket] and log_cache:
        await websocket.send_json({'type': 'log_history', 'data': list(log_cache)})


async def _handle_unsubscribe(websocket: WebSocket, events: list) -> None:
    """处理取消订阅请求。"""
    ws_clients[websocket] -= set(events)
    await websocket.send_json({'type': 'subscribed', 'events': list(ws_clients[websocket])})
