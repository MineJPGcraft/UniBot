"""数据统计管理器测试：收发计数、趋势、群聊活跃度与持久化。"""

import asyncio

from Scripts.Managers.Statistics import StatisticsManager


def _manager(tmp_path) -> StatisticsManager:
    """构建指向临时目录的管理器实例，避免触碰真实数据文件。"""
    manager = StatisticsManager()
    manager.statistics_file = tmp_path / 'Statistics.json'
    return manager


def test_record_sent_and_received(tmp_path) -> None:
    manager = _manager(tmp_path)
    for _ in range(3):
        manager.record_sent('group')
    manager.record_sent('unknown')
    manager.record_received('QQ')
    manager.record_received('QQ', group_key='qq_client:123', group_name='测试群')

    summary = manager.summary()
    assert summary['sent_total'] == 4
    assert summary['sent_group'] == 3
    assert summary['received_total'] == 2
    assert summary['group_received_total'] == 1
    assert summary['private_received_total'] == 1
    assert summary['active_groups_today'] == 1
    assert summary['tracked_groups'] == 1


def test_trend_fills_missing_days(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.record_received('QQ', group_key='qq_client:123')
    trend = manager.trend(7)
    assert len(trend) == 7
    today = trend[-1]
    assert today['received'] == 1
    assert today['active_groups'] == 1
    # 其余日期补零
    assert all(day['received'] == 0 for day in trend[:-1])


def test_top_groups_sorted_by_last_active(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.record_received('QQ', group_key='qq_client:a', group_name='旧群')
    manager.record_received('QQ', group_key='qq_client:b', group_name='新群')
    # 后写入的群 last_active 更新，应排在前面
    top_keys = [entry['key'] for entry in manager.top_groups()]
    assert top_keys == ['qq_client:b', 'qq_client:a']
    assert manager.top_groups()[0]['name'] == '新群'


def test_platform_rank(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.record_received('QQ')
    manager.record_received('MC')
    manager.record_received('QQ')
    platforms = manager.platform_rank()
    assert platforms[0] == {'platform': 'QQ', 'count': 2}


def test_save_and_load_roundtrip(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.record_sent('group')
    manager.record_received('QQ', group_key='qq_client:123', group_name='测试群')
    asyncio.run(manager.save())

    reloaded = _manager(tmp_path)
    reloaded.load()
    summary = reloaded.summary()
    assert summary['sent_total'] == 1
    assert summary['received_total'] == 1
    assert reloaded.groups['qq_client:123']['name'] == '测试群'
    assert not reloaded.dirty


def test_load_corrupted_file_falls_back_to_empty(tmp_path) -> None:
    (tmp_path / 'Statistics.json').write_text('{broken json', encoding='Utf-8')
    manager = _manager(tmp_path)
    manager.load()
    assert manager.received_total == 0
    assert manager.groups == {}


def test_reset_clears_all_counters(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.record_sent('group')
    manager.record_received('QQ', group_key='qq_client:123')
    manager.reset()
    summary = manager.summary()
    assert summary['sent_total'] == 0
    assert summary['received_total'] == 0
    assert manager.daily == {}
    assert manager.groups == {}
    assert manager.dirty
