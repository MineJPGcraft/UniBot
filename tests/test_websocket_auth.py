"""WebSocket 认证与广播测试：默认拒绝 query token、广播遍历使用快照。"""

import asyncio

from Core.Web.Managers import data_manager
from Core.Web.Routers import WebSocket as ws_module
from Core.Web.Routers.Auth import COOKIE_ACCESS_KEY, create_access_token


class _FakeWebSocket:
    """最小 WebSocket 桩：记录关闭状态，可配置 send_json 行为。"""

    def __init__(self, *, cookies: dict | None = None, query: dict | None = None, fail_send: bool = False) -> None:
        self.cookies = cookies or {}
        self.query_params = query or {}
        self.fail_send = fail_send
        self.closed = False
        self.close_code: int | None = None
        self.sent: list[dict] = []

    async def close(self, code: int = 1000, reason: str = '') -> None:
        self.closed = True
        self.close_code = code

    async def send_json(self, message: dict) -> None:
        if self.fail_send:
            raise RuntimeError('client gone')
        self.sent.append(message)


def _valid_token() -> str:
    """用当前数据管理器的密钥签发一个合法 access_token。"""
    data_manager.secret_key = 'unit-test-secret-unit-test-secret-0123456789'
    return create_access_token('u_test', 'admin')


def test_cookie_token_authenticates():
    """同源 cookie 中的合法 access_token 通过认证。"""
    websocket = _FakeWebSocket(cookies={COOKIE_ACCESS_KEY: _valid_token()})
    assert asyncio.run(ws_module._authenticate_websocket(websocket)) is True
    assert websocket.closed is False


def test_query_token_rejected_by_default():
    """默认不接受 URL query 中的 token，即使其本身合法。"""
    websocket = _FakeWebSocket(query={'token': _valid_token()})
    assert ws_module.ALLOW_QUERY_TOKEN is False
    assert asyncio.run(ws_module._authenticate_websocket(websocket)) is False
    assert websocket.closed is True
    assert websocket.close_code == 4001


def test_query_token_opt_in(monkeypatch):
    """显式开启兼容后，query token 才被接受。"""
    monkeypatch.setattr(ws_module, 'ALLOW_QUERY_TOKEN', True)
    websocket = _FakeWebSocket(query={'token': _valid_token()})
    assert asyncio.run(ws_module._authenticate_websocket(websocket)) is True


def test_broadcast_uses_snapshot_and_prunes_failures():
    """广播遍历使用连接快照，发送失败的连接被剔除且不抛错。"""
    alive = _FakeWebSocket()
    gone = _FakeWebSocket(fail_send=True)
    ws_module.ws_clients.clear()
    ws_module.ws_clients[alive] = {'log'}
    ws_module.ws_clients[gone] = {'log'}
    try:
        asyncio.run(ws_module.broadcast_event('log', {'message': 'hi'}))
    finally:
        ws_module.ws_clients.clear()

    assert alive.sent == [{'type': 'log', 'data': {'message': 'hi'}}]
    # 发送失败的连接已被清理，成功的保留
    assert gone not in ws_module.ws_clients
    assert alive not in ws_module.ws_clients  # 测试后清空
