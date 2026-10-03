"""QQ 官方机器人「指令面板」开放接口客户端。

继承 `BasePanelClient`，实现 QQ 专属逻辑：
  - 凭证：POST /app/getAppAccessToken，AppID + ClientSecret 换 access_token
    （有效期约 7200 秒，客户端内部提前刷新，调用方无需关心）
  - 面板 CRUD：POST/GET /v2/panels、GET/PUT/DELETE /v2/panels/{panel_id}
  - 关联对象：PUT /v2/panels/{panel_id}/target

场景 scope：c2c（单聊）/ group（群聊）/ channel（文字子频道）/ dm（频道私信）。
鉴权请求头格式：Authorization: QQBot <access_token>。
"""

from __future__ import annotations

import time

import httpx

from Scripts.Constants import (
    QQ_OPEN_API_BASE,
    QQ_OPEN_API_PANELS_PATH,
    QQ_OPEN_API_TOKEN_PATH,
    QQ_PANEL_TOKEN_REFRESH_MARGIN_SECONDS,
)
from Scripts.Platforms.Panels.Base import (
    BasePanelClient,
    PanelError,
    build_panel_body,
)

# 官方限制：一个机器人最多 20 个面板（每面板元素上限见 Base.MAX_ITEMS_PER_PANEL）
MAX_PANELS_PER_BOT = 20

# 兼容导出：QQ 错误即通用面板错误（其它平台共用 PanelError）
QQPanelError = PanelError


class QQPanelClient(BasePanelClient):
    """单个 QQ 机器人的面板接口客户端（含 access_token 缓存与自动刷新）。"""

    def __init__(
        self,
        app_id: str,
        client_secret: str,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url=QQ_OPEN_API_BASE, timeout=timeout, client=client)
        self.app_id = app_id
        self.client_secret = client_secret
        self._token = ''
        self._token_expires_at = 0.0

    # ----- 凭证 -----

    async def _auth_headers(self) -> dict | None:
        """QQ 鉴权请求头：Authorization: QQBot <access_token>。"""
        return {'Authorization': f'QQBot {await self._get_token()}'}

    async def _get_token(self) -> str:
        """获取 access_token，过期前自动刷新并缓存复用。"""
        now = time.monotonic()
        if self._token and now < self._token_expires_at - QQ_PANEL_TOKEN_REFRESH_MARGIN_SECONDS:
            return self._token
        payload = {'appId': self.app_id, 'clientSecret': self.client_secret}
        data = await self._request(
            'POST',
            QQ_OPEN_API_TOKEN_PATH,
            json=payload,
            with_auth=False,
        )
        token = data.get('access_token')
        expires_in = int(data.get('expires_in') or 7200)
        if not token:
            raise PanelError(f'获取 access_token 失败：{data}！')
        self._token = str(token)
        self._token_expires_at = now + expires_in
        return self._token

    # ----- 面板接口 -----

    async def create_panel(
        self,
        scope: str,
        panel_items: list[dict],
        *,
        target_type: str = 'all',
        group_openids: list[str] | None = None,
        user_openids: list[str] | None = None,
        remark: str = '',
    ) -> str:
        """创建指令面板，返回 panel_id。

        Args:
            scope: 生效场景（c2c/group/channel/dm）
            panel_items: 面板元素列表，元素结构 {'type': 'command'|'link', 'name': ..., 'desc': ..., 'link': ...}
            target_type: all（全局）/ specific（指定用户/群，仅 c2c/group）
            group_openids: 群 openid 列表（group 场景 specific 时有效，最多 20 个）
            user_openids: 用户 openid 列表（c2c 场景 specific 时有效，最多 20 个）
            remark: 面板备注（开发者可见，最多 255 字符）
        """
        payload: dict = {
            'scope': scope,
            'target_type': target_type,
            'panel': build_panel_body(panel_items, remark),
        }
        if target_type == 'specific':
            if group_openids:
                payload['group_openids'] = group_openids
            if user_openids:
                payload['user_openids'] = user_openids
        data = await self._request('POST', QQ_OPEN_API_PANELS_PATH, json=payload)
        panel_id = data.get('panel_id')
        if not panel_id:
            raise PanelError(f'创建面板成功但未返回 panel_id：{data}！')
        return str(panel_id)

    async def list_panels(self, scope: str, *, limit: int = 50) -> list[dict]:
        """查询指定场景的面板列表，自动翻页直到拉取完全部面板。

        官方接口分页：cursor / next_cursor / is_end，单页最多 50 条；
        返回的 records 按设置时间倒序（最新在前）。
        """
        records: list[dict] = []
        cursor = ''
        while True:
            params: dict = {'scope': scope, 'limit': limit}
            if cursor:
                params['cursor'] = cursor
            data = await self._request('GET', QQ_OPEN_API_PANELS_PATH, params=params)
            page_records = data.get('records') or []
            if isinstance(page_records, list):
                records.extend(page_records)
            next_cursor = data.get('next_cursor') or ''
            if data.get('is_end') or not next_cursor:
                break
            cursor = next_cursor
        return records

    async def get_panel(self, panel_id: str) -> dict:
        """查询面板详情（含关联 openid 列表）。"""
        return await self._request('GET', f'{QQ_OPEN_API_PANELS_PATH}/{panel_id}')

    async def update_panel(self, panel_id: str, panel_items: list[dict], *, remark: str = '') -> int:
        """修改面板元素（覆盖式，不影响已关联的用户/群），返回新版本号。"""
        data = await self._request(
            'PUT',
            f'{QQ_OPEN_API_PANELS_PATH}/{panel_id}',
            json={'panel': build_panel_body(panel_items, remark)},
        )
        return int(data.get('version') or 0)

    async def delete_panel(self, panel_id: str) -> None:
        """删除面板，成功无响应体。"""
        await self._request('DELETE', f'{QQ_OPEN_API_PANELS_PATH}/{panel_id}')

    async def update_panel_targets(
        self,
        panel_id: str,
        op: str,
        *,
        group_openids: list[str] | None = None,
        user_openids: list[str] | None = None,
    ) -> None:
        """添加/移除面板关联的用户或群（op: add / del，一次最多 20 个 openid）。"""
        payload: dict = {'op': op}
        if group_openids:
            payload['group_openids'] = group_openids
        if user_openids:
            payload['user_openids'] = user_openids
        await self._request(
            'PUT',
            f'{QQ_OPEN_API_PANELS_PATH}/{panel_id}/target',
            json=payload,
        )
