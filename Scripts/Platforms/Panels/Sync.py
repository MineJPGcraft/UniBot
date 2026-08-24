"""QQ 指令面板同步：机器人连接后自动把 UniBot 指令同步为 QQ 群指令面板。

流程（连接时调用 `sync_panels_for_all_bots`）：
  1. 读取 .env 的 `QQ_BOTS` 凭据（AppID + ClientSecret）
  2. 从命令注册表把全部指令构建为面板元素（name ≤ 14 字符 / desc ≤ 30 字符，最多 20 个）
  3. 对每个机器人查询 group 场景既有面板（自动翻页拉全），remark 为 `UniBot` 的复用更新，
     否则创建 `target_type=all` 的全局面板（对所有群生效，无需逐群绑定）
  4. 创建时若面板数量已达上限（官方错误 40030013），自动清理最旧的
     非 `UniBot` 面板（覆盖全部生效场景）腾出名额后重试一次

任何失败只告警不抛出，保证不阻断机器人启动。
"""

from __future__ import annotations

from nonebot.log import logger

from Scripts.Extensions import command_manager
from Scripts.Managers import config_manager
from Scripts.Platforms.Panels.Base import MAX_ITEMS_PER_PANEL, PanelError
from Scripts.Platforms.Panels.QQ import MAX_PANELS_PER_BOT, QQPanelClient

# 识别 UniBot 接管面板的固定备注（开发者手建的面板不会被误动）
PANEL_REMARK = 'UniBot'
# 面板元素字段上限（官方限制）
MAX_ITEM_NAME_LENGTH = 14
MAX_ITEM_DESC_LENGTH = 15
# 面板数量超限（超出数量限制）的官方错误码
ERR_PANEL_LIMIT = 40030013
# 超限时最多清理的旧面板数量
MAX_CLEANUP_PANELS = 3
# 20 个面板上限为机器人全局限制（跨全部生效场景），清理需覆盖所有场景
PANEL_SCOPES = ('c2c', 'group', 'channel', 'dm')


def _build_panel_items() -> list[dict]:
    """从命令注册表构建面板元素列表，超出面板上限时截断并告警。"""
    items: list[dict] = []
    for command in command_manager.get_command_nodes().values():
        name = command.name[:MAX_ITEM_NAME_LENGTH]
        desc = (command.description or '')[:MAX_ITEM_DESC_LENGTH]
        items.append({'type': 'command', 'name': name, 'desc': desc})
        if len(items) >= MAX_ITEMS_PER_PANEL - 1:
            break
    items.append({'type': 'link', 'name': '指令手册', 'link': 'https://bot.mcjpg.dev/guide/command-reference.html'})
    if not items:
        logger.warning('No commands available, skipping QQ panel sync!')
    return items


async def _cleanup_stale_panels(client: QQPanelClient) -> int:
    """删除最旧的非 UniBot 面板腾出名额，返回删除数量（最多 MAX_CLEANUP_PANELS 个）。"""
    stale_panels: list[tuple[str, str]] = []
    for scope in PANEL_SCOPES:
        for panel in await client.list_panels(scope):
            if (panel.get('panel') or {}).get('remark') != PANEL_REMARK:
                panel_id = panel.get('panel_id')
                if panel_id:
                    # records 按设置时间倒序，越靠后越旧
                    stale_panels.append((str(panel_id), str(scope)))
    removed = 0
    for panel_id, scope in stale_panels[-MAX_CLEANUP_PANELS:]:
        try:
            await client.delete_panel(panel_id)
        except PanelError as error:
            logger.warning(f'Failed to clean up stale panel: {panel_id} ({scope}) {error}!')
            continue
        logger.warning(f'Cleaned up stale panel: {panel_id} ({scope}) to free up a slot!')
        removed += 1
    return removed


async def _sync_one_bot(app_id: str, client_secret: str, panel_items: list[dict]) -> None:
    """把指令同步到单个机器人的 group 全局面板：无则创建，有则更新。"""
    async with QQPanelClient(app_id=app_id, client_secret=client_secret) as client:
        existing = await client.list_panels('group')
        managed = next(
            (panel for panel in existing if (panel.get('panel') or {}).get('remark') == PANEL_REMARK),
            None,
        )
        if managed is not None:
            panel_id = managed.get('panel_id')
            await client.update_panel(str(panel_id), panel_items, remark=PANEL_REMARK)
            logger.success(f'Updated group-wide command panel for bot {app_id}: {panel_id}')
            return
        # 无 UniBot 面板：创建；若面板数量已达上限，清理旧面板后重试一次
        try:
            panel_id = await client.create_panel(
                'group',
                panel_items,
                target_type='all',
                remark=PANEL_REMARK,
            )
        except PanelError as error:
            if error.code != ERR_PANEL_LIMIT:
                raise
            panel_limit = (error.details or {}).get('limit') or MAX_PANELS_PER_BOT
            logger.warning(
                f'Bot {app_id} has reached the panel limit ({panel_limit}), cleaning up stale panels and retrying: {error}!'
            )
            if await _cleanup_stale_panels(client) == 0:
                raise
            panel_id = await client.create_panel(
                'group',
                panel_items,
                target_type='all',
                remark=PANEL_REMARK,
            )
        logger.success(f'Created group-wide command panel for bot {app_id}: {panel_id}')


async def sync_panels_for_all_bots() -> None:
    """为 .env 中配置的每个 QQ 机器人同步群指令面板。"""
    bots = config_manager.read_env().get('QQ_BOTS') or []
    if not bots:
        logger.info('QQ_BOTS not configured, skipping panel sync!')
        return
    panel_items = _build_panel_items()
    for bot in bots:
        app_id = str(bot.get('id') or '')
        client_secret = str(bot.get('secret') or '')
        if not app_id or not client_secret:
            logger.warning(f'QQ bot missing AppID/Secret, skipping panel sync: {bot}')
            continue
        try:
            await _sync_one_bot(app_id, client_secret, panel_items)
        except PanelError as error:
            logger.warning(f'Failed to sync panel for QQ bot {app_id}: {error}')
        except Exception as error:
            logger.warning(f'Failed to sync panel for QQ bot {app_id}: {error}')
