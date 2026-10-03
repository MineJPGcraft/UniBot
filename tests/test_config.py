"""配置管理器测试：.env 解析（含多行值）、写回 round-trip。"""

from pathlib import Path

from Core.Managers.Config import ConfigManager


def _manager(tmp_path: Path, content: str) -> ConfigManager:
    """在临时目录构造带指定内容的 ConfigManager。"""
    manager = ConfigManager()
    manager.env_path = tmp_path / '.env'
    manager.env_path.write_text(content, encoding='Utf-8')
    manager.load_env()
    return manager


def test_load_env_multiline_plain(tmp_path):
    """纯文本多行值（变量后面换行）不应报错，且保留换行。"""
    manager = _manager(tmp_path, 'A=1\nB=line1\nline2\nC=3\n')
    assert manager.environment['B'] == 'line1\nline2'
    assert manager.environment['A'] == 1
    assert manager.environment['C'] == 3


def test_load_env_multiline_quoted(tmp_path):
    """引号包裹的多行值：去掉首尾引号并保留内部换行。"""
    manager = _manager(tmp_path, 'A=1\nB="line1\nline2"\nC=3\n')
    assert manager.environment['B'] == 'line1\nline2'


def test_load_env_escaped_multiline_roundtrip(tmp_path):
    """写回格式（单行转义 \\n）能正确解析，且写回后读回一致。"""
    manager = _manager(tmp_path, 'A=1\nB="line1\\nline2"\nC=3\n')
    assert manager.environment['B'] == 'line1\nline2'

    manager.update_env({'D': 'x'})
    manager2 = ConfigManager()
    manager2.env_path = manager.env_path
    manager2.load_env()
    assert manager2.environment['B'] == 'line1\nline2'
    assert manager2.environment['D'] == 'x'


def test_load_env_quoted_json(tmp_path):
    """引号包裹的 JSON 对象：去掉外层引号后解析为 dict；普通引号串仍是字符串。"""
    manager = _manager(tmp_path, 'B="{"A":"B"}"\nC="[1, 2]"\nD=[1, 2]\n')
    assert manager.environment['B'] == {'A': 'B'}
    # 外层引号是字符串语法，整体是合法 JSON 字符串，保持为字符串
    assert manager.environment['C'] == '[1, 2]'
    # 不带外层引号才是列表
    assert manager.environment['D'] == [1, 2]


def test_load_env_json_and_comments(tmp_path):
    """单行 JSON 值、注释、空行混排仍正常工作。"""
    manager = _manager(tmp_path, '# 注释\n\nA=1\n\nB=["x", "y"]\n')
    assert manager.environment['A'] == 1
    assert manager.environment['B'] == ['x', 'y']
    # 注释与空行保留在 mapping 中，写回不丢失
    manager.update_env({'C': 'z'})
    content = manager.env_path.read_text('Utf-8')
    assert '# 注释' in content
    assert 'C="z"' in content
