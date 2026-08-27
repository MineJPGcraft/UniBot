"""指令面板对接层：通用基类 + QQ 官方开放平台客户端 + 连接时全群同步。"""

from Scripts.Platforms.Panels.Base import (
    MAX_ITEMS_PER_PANEL,
    BasePanelClient,
    PanelError,
    build_panel_body,
)
from Scripts.Platforms.Panels.QQ import MAX_PANELS_PER_BOT, QQPanelClient
from Scripts.Platforms.Panels.Sync import remove_panels_for_all_bots, sync_panels_for_all_bots

__all__ = [
    'MAX_ITEMS_PER_PANEL',
    'MAX_PANELS_PER_BOT',
    'BasePanelClient',
    'PanelError',
    'QQPanelClient',
    'build_panel_body',
    'remove_panels_for_all_bots',
    'sync_panels_for_all_bots',
]
