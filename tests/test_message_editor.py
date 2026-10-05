"""消息文本编辑器后端测试：命名空间树构建（过滤系统键）与覆盖层保存（仅存改动、剔除受保护键）。"""

from pathlib import Path

import pytest

from Core.I18n import register_all
from Core.Web.Routers.Config.Messages import build_message_tree, save_overrides


def _iter_nodes(nodes):
    """深度遍历命名空间节点。"""
    for node in nodes:
        yield node
        yield from _iter_nodes(node['children'])


def _keys(tree: dict) -> set[str]:
    """收集树中全部叶子消息键。"""
    keys: set[str] = set()
    for node in _iter_nodes(tree['tree']):
        keys.update(item['key'] for item in node['items'])
    return keys


def _find_item(tree: dict, key: str) -> dict:
    """按点路径取出某条消息项。"""
    for node in _iter_nodes(tree['tree']):
        for item in node['items']:
            if item['key'] == key:
                return item
    raise AssertionError(f'{key} not found in message tree')


def test_tree_is_namespace_nested() -> None:
    tree = build_message_tree('zh')
    # 顶层含 core 命名空间，且 core 下有 commands / events 子命名空间
    roots = {node['name'] for node in tree['tree']}
    assert 'core' in roots
    core = next(node for node in tree['tree'] if node['name'] == 'core')
    child_names = {child['name'] for child in core['children']}
    assert {'commands', 'events'} <= child_names
    # core.commands 下再按指令名分层
    commands = next(child for child in core['children'] if child['name'] == 'commands')
    assert any(child['name'] == 'luck' for child in commands['children'])


def test_tree_node_counts_aggregate_subtree() -> None:
    tree = build_message_tree('zh')
    core = next(node for node in tree['tree'] if node['name'] == 'core')
    # 子树计数 = 本层叶子 + 全部子命名空间叶子
    assert core['count'] == sum(child['count'] for child in core['children']) + len(core['items'])
    assert core['count'] > 0


def test_tree_excludes_protected_keys() -> None:
    tree = build_message_tree('zh')
    keys = _keys(tree)
    # 用户可改的消息键在树中
    assert 'core.events.player_join' in keys
    # 系统键（api.* / builtin.* / core.commands.bot.*）不下发
    assert not any(key.startswith('api.') for key in keys)
    assert not any(key.startswith('builtin.') for key in keys)
    assert not any(key.startswith('core.commands.bot') for key in keys)


def test_tree_item_carries_placeholders_and_base() -> None:
    tree = build_message_tree('zh')
    item = _find_item(tree, 'core.events.player_join')
    assert 'player' in item['placeholders']
    assert item['value'] == item['base_value']
    assert item['modified'] is False


@pytest.fixture
def _temp_override(monkeypatch, tmp_path: Path):
    """把覆盖层路径重定向到临时目录，测试后恢复语言包注册。"""
    monkeypatch.setattr(
        'Core.I18n.Loader.OVERRIDE_MESSAGE_PATHS',
        {'zh': tmp_path / 'Messages.zh.toml', 'en': tmp_path / 'Messages.en.toml'},
    )
    yield tmp_path
    monkeypatch.undo()
    register_all()


def test_save_prunes_protected_and_unchanged(_temp_override: Path) -> None:
    count = save_overrides(
        'zh',
        {
            'core.events.player_join': '改名：{player} 上线',  # 改动 → 保留
            'core.events.player_quit': '玩家 {player} 离开了游戏。',  # 等于默认 → 丢弃
            'api.auth.token_expired': '篡改',  # 受保护 → 丢弃
            'builtin.list.name': '篡改',  # 受保护 → 丢弃
        },
    )
    assert count == 1
    content = (_temp_override / 'Messages.zh.toml').read_text('Utf-8')
    assert 'player_join' in content
    assert 'player_quit' not in content
    assert 'token_expired' not in content
    assert 'builtin' not in content


def test_saved_override_takes_effect(_temp_override: Path) -> None:
    save_overrides('zh', {'core.events.player_join': '改名：{player} 上线'})
    tree = build_message_tree('zh')
    item = _find_item(tree, 'core.events.player_join')
    assert item['value'] == '改名：{player} 上线'
    assert item['modified'] is True
