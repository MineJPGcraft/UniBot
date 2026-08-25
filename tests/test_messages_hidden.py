"""消息包隐藏区块（Hidden Start / Hidden End）测试。"""

from Scripts.Messages import (
    restore_hidden_content,
    strip_hidden_content,
)


def test_strip_removes_markers_and_inner_completely() -> None:
    content = '\n'.join(
        [
            '[events]',
            'player_join = "join"',
            '# Hidden Start',
            'secret = "do not show"',
            '# Hidden End',
            '[commands.send]',
            'sent = "ok"',
        ]
    )
    stripped = strip_hidden_content(content)
    assert 'secret' not in stripped
    assert 'Hidden' not in stripped
    assert stripped == '[events]\nplayer_join = "join"\n[commands.send]\nsent = "ok"\n'


def test_strip_handles_multiple_and_unclosed_blocks() -> None:
    content = '\n'.join(
        [
            '# Hidden Start',
            'a = 1',
            '# Hidden End',
            'key = "value"',
            '# Hidden Start',
            'b = 2',
        ]
    )
    assert strip_hidden_content(content) == 'key = "value"\n'


def test_restore_reinserts_blocks_at_original_position() -> None:
    disk = '\n'.join(
        [
            '[events]',
            '# Hidden Start',
            'first = 1',
            '# Hidden End',
            'player_join = "join"',
            '# Hidden Start',
            'second = 2',
            '# Hidden End',
            '[commands.send]',
        ]
    )
    incoming = strip_hidden_content(disk)
    restored = restore_hidden_content(incoming, disk)
    assert restored == disk + '\n'


def test_restore_discards_submitted_markers_and_keeps_disk_content() -> None:
    disk = '\n'.join(['[events]', '# Hidden Start', 'keep_me = 1', '# Hidden End'])
    # WebUI 提交内容里即使被手动塞入标记与伪造内容，也一律以磁盘为准
    incoming = '\n'.join(['[events]', '# Hidden Start', 'evil = 999', '# Hidden End'])
    restored = restore_hidden_content(incoming, disk)
    assert 'keep_me = 1' in restored and 'evil' not in restored
    assert restored.count('# Hidden Start') == 1 and restored.count('# Hidden End') == 1


def test_restore_appends_block_when_anchor_missing() -> None:
    disk = '\n'.join(['[events]', 'anchor_line = "x"', '# Hidden Start', 'hidden = 1', '# Hidden End'])
    # 锚点行被用户删除：隐藏块自动追加到末尾（含完整标记），数据不丢
    incoming = '[events]\nother = "edited"'
    restored = restore_hidden_content(incoming, disk)
    lines = restored.splitlines()
    assert lines[:2] == ['[events]', 'other = "edited"']
    assert lines[-3:] == ['# Hidden Start', 'hidden = 1', '# Hidden End']


def test_restore_puts_head_block_back_at_top() -> None:
    disk = '\n'.join(['# Hidden Start', 'head = 1', '# Hidden End', '[events]', 'player_join = "join"'])
    restored = restore_hidden_content(strip_hidden_content(disk), disk)
    assert restored.splitlines()[0] == '# Hidden Start'
    assert 'head = 1' in restored and 'player_join = "join"' in restored


def test_restore_round_trip_is_stable() -> None:
    disk = '\n'.join(
        ['[events]', 'player_join = "join"', '', '# Hidden Start', 'hidden = 1', '# Hidden End', '', '[commands]']
    )
    once = restore_hidden_content(strip_hidden_content(disk), disk)
    twice = restore_hidden_content(once, disk)
    assert twice == once == disk + '\n'
