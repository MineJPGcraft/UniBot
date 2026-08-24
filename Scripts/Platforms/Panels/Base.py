"""面板对接层基类：跨平台指令面板客户端的公共基础设施。

子类只需继承 `BasePanelClient` 并实现平台专属逻辑：
  - 覆盖 `_auth_headers()` 提供平台鉴权头（如 QQ 的 `Authorization: QQBot <token>`）
  - 基于 `_request()` / `_parse_response()` 实现平台面板 CRUD
  - 共享 `build_panel_body()` 统一构造面板体并校验元素数量

新增平台（Telegram / Discord / 飞书……）时：新建 `Scripts/Platforms/Panels/<Platform>.py`，
继承本基类，即可复用 HTTP client、请求发送、错误解析与面板体构造。
"""

from __future__ import annotations

from typing import Self

import httpx

# 面板通用上限：一个面板最多 20 个元素（主流平台一致，子类可按需覆盖）
MAX_ITEMS_PER_PANEL = 20


class PanelError(RuntimeError):
    """面板接口错误（含平台错误码、信息与原始响应体）。"""

    def __init__(self, message: str, code: int | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        # 原始响应体：部分错误（如 QQ 的 40030013）会携带 limit 等附加字段
        self.details = details


class BasePanelClient:
    """面板客户端基类：提供共享 HTTP client、请求发送与响应解析。"""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        # 允许调用方传入共享 client（便于连接复用与统一关闭）
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> Self:
        self._ensure_client()
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """释放自建的 HTTP client（外部传入的 client 由调用方管理）。"""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
            self._owns_client = True
        return self._client

    async def _auth_headers(self) -> dict | None:
        """返回平台鉴权请求头；无鉴权时返回 None。子类覆盖。"""
        return None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        with_auth: bool = True,
    ) -> dict:
        """发送请求并解析 JSON，非 2xx 或带错误码时抛 PanelError。"""
        auth_headers = await self._auth_headers() if with_auth else None
        merged = {**(auth_headers or {}), **(headers or {})}
        client = self._ensure_client()
        try:
            response = await client.request(
                method,
                path,
                json=json,
                params=params,
                headers=merged or None,
            )
        except httpx.HTTPError as error:
            raise PanelError(f'Panel API request failed: {method} {path}, {error}!') from error
        return self._parse_response(response, method, path)

    @staticmethod
    def _parse_response(response: httpx.Response, method: str, path: str) -> dict:
        """解析响应 JSON：非 2xx 或业务错误码时抛 PanelError。"""
        try:
            data = response.json()
        except Exception as error:
            raise PanelError(
                f'Panel API response is not JSON: {method} {path} HTTP {response.status_code}, {response.text!r}'
            ) from error
        if not isinstance(data, dict):
            return {}
        # QQ 等平台错误响应形如 {"code": 40030013, "message": ..., "trace_id": ...}，
        # 部分平台用 err_code 字段，这里两种命名都兼容
        error_code = data.get('code', data.get('err_code'))
        if response.status_code // 100 != 2:
            raise PanelError(
                f'Panel API returned an error: {method} {path} HTTP {response.status_code}, {data.get("message") or data}',
                code=error_code,
                details=data,
            )
        if 'code' in data and data.get('code') not in (0, 200):
            raise PanelError(
                f'Panel API returned an error: {method} {path}, {data.get("message") or data}',
                code=error_code,
                details=data,
            )
        return data


def build_panel_body(panel_items: list[dict], remark: str) -> dict:
    """构造请求体中的 panel 对象，并做元素数量上限校验。"""
    if len(panel_items) > MAX_ITEMS_PER_PANEL:
        raise PanelError(f'Panel items exceed the limit: {len(panel_items)} > {MAX_ITEMS_PER_PANEL}!')
    panel: dict = {'items': panel_items}
    if remark:
        panel['remark'] = remark
    return panel
