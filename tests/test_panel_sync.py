"""QQ 指令面板同步测试。

覆盖：
  - 开关开启时正常同步（创建/更新面板）
  - 开关关闭时不再同步，改为删除遗留的 UniBot 面板
  - 遗留面板清理覆盖全部生效场景，且只删除 remark 为 UniBot 的面板
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from Scripts.Platforms.Panels import Sync as panel_sync
from Scripts.Platforms.Panels.Sync import (
    PANEL_REMARK,
    _remove_managed_panels,
    remove_panels_for_all_bots,
    sync_panels_for_all_bots,
)


def _panel_record(panel_id: str, remark: str) -> dict:
    """构造 list_panels 返回的单条面板记录。"""
    return {'panel_id': panel_id, 'panel': {'remark': remark}}


def _patched_client(fake_client):
    """构造补丁：QQPanelClient(...) 返回的实例作为异步上下文管理器时产出 fake_client。"""
    client_class = MagicMock()
    # patch 的 return_value 即调用 QQPanelClient(...) 的返回值，直接在其上配置 __aenter__
    client_class.__aenter__.return_value = fake_client
    return patch.object(panel_sync, 'QQPanelClient', return_value=client_class)


def test_sync_skipped_when_no_bots():
    """未配置 QQ_BOTS 时直接跳过，不创建任何客户端。"""
    with (
        patch.object(panel_sync.config_manager, 'read_env', return_value={}),
        patch.object(panel_sync, 'QQPanelClient') as client_class,
    ):
        asyncio.run(sync_panels_for_all_bots())
        client_class.assert_not_called()


def test_sync_creates_panel_when_enabled(monkeypatch):
    """开关开启时应为每个机器人创建全局面板。"""
    monkeypatch.setattr(panel_sync.config, 'sync_command_panels', True)
    fake_client = AsyncMock()
    fake_client.list_panels.return_value = []
    fake_client.create_panel.return_value = 'panel-1'
    with (
        patch.object(
            panel_sync.config_manager,
            'read_env',
            return_value={'QQ_BOTS': [{'id': 'app-1', 'secret': 'secret-1'}]},
        ),
        _patched_client(fake_client),
    ):
        asyncio.run(sync_panels_for_all_bots())
    fake_client.create_panel.assert_awaited_once()
    args = fake_client.create_panel.await_args.args
    kwargs = fake_client.create_panel.await_args.kwargs
    assert args[0] == 'group'
    assert kwargs == {'target_type': 'all', 'remark': PANEL_REMARK}
    fake_client.delete_panel.assert_not_called()


def test_sync_removes_leftover_panels_when_disabled(monkeypatch):
    """开关关闭时不应创建/更新面板，而应删除遗留的 UniBot 面板。"""
    monkeypatch.setattr(panel_sync.config, 'sync_command_panels', False)
    fake_client = AsyncMock()
    # group 场景有一个 UniBot 面板 + 一个第三方面板；c2c 场景有一个 UniBot 面板
    fake_client.list_panels.side_effect = lambda scope: {
        'group': [_panel_record('panel-managed', PANEL_REMARK), _panel_record('panel-other', 'Other')],
        'c2c': [_panel_record('panel-c2c', PANEL_REMARK)],
    }.get(scope, [])
    with (
        patch.object(
            panel_sync.config_manager,
            'read_env',
            return_value={'QQ_BOTS': [{'id': 'app-1', 'secret': 'secret-1'}]},
        ),
        _patched_client(fake_client),
    ):
        asyncio.run(sync_panels_for_all_bots())
    fake_client.create_panel.assert_not_called()
    fake_client.update_panel.assert_not_called()
    # 只删除 UniBot 面板，且覆盖 group 与 c2c 场景
    deleted = [call.args[0] for call in fake_client.delete_panel.await_args_list]
    assert sorted(deleted) == ['panel-c2c', 'panel-managed']


def test_remove_managed_panels_only_deletes_unibot_remark():
    """清理函数只删除 remark 为 UniBot 的面板。"""
    fake_client = AsyncMock()
    fake_client.list_panels.side_effect = lambda scope: {
        'group': [
            _panel_record('keep-me', 'Manual'),
            _panel_record('drop-me', PANEL_REMARK),
        ],
    }.get(scope, [])
    removed = asyncio.run(_remove_managed_panels(fake_client))
    assert removed == 1
    fake_client.delete_panel.assert_awaited_once_with('drop-me')


def test_remove_panels_for_all_bots_reads_env_when_not_given():
    """不传 bots 时应自行读取 .env 的 QQ_BOTS，并删除各场景的遗留面板。"""
    fake_client = AsyncMock()
    # 每个场景都返回同一条记录，验证清理覆盖全部生效场景
    fake_client.list_panels.return_value = [_panel_record('panel-x', PANEL_REMARK)]
    with (
        patch.object(
            panel_sync.config_manager,
            'read_env',
            return_value={'QQ_BOTS': [{'id': 'app-1', 'secret': 'secret-1'}]},
        ),
        _patched_client(fake_client),
    ):
        asyncio.run(remove_panels_for_all_bots())
    assert fake_client.delete_panel.await_count == len(panel_sync.PANEL_SCOPES)
    fake_client.delete_panel.assert_any_await('panel-x')
