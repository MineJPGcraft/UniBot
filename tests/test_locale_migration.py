"""旧消息包迁移测试：把旧 Config/Messages.*.toml 的用户改动并入 Core/Locales/Messages.*.toml，幂等。

迁移脚本完全独立（`Scripts/migrate_messages.py`，零 Core 依赖），测试直接导入该模块并
monkeypatch 其自带的路径常量。
"""

from pathlib import Path

import pytest

from Scripts import migrate_messages


@pytest.fixture
def _temp_paths(monkeypatch, tmp_path: Path):
    """把迁移源/目标/标记重定向到临时目录。"""
    locales_dir = tmp_path / 'Locales'
    messages_zh = locales_dir / 'Messages.zh.toml'
    legacy = tmp_path / 'LegacyMessages.zh.toml'
    legacy.write_text('[events]\nplayer_join = "玩家 {player} 上线啦！"\n', encoding='Utf-8')
    marker = locales_dir / '.migrated'
    monkeypatch.setattr(migrate_messages, 'LOCALES_DIR', locales_dir)
    monkeypatch.setattr(migrate_messages, 'MIGRATION_MARKER_PATH', marker)
    monkeypatch.setattr(
        migrate_messages, 'MESSAGE_PATHS', {'zh': messages_zh, 'en': tmp_path / 'missing.en.toml'}
    )
    monkeypatch.setattr(
        migrate_messages,
        'LEGACY_MESSAGE_PATHS',
        {'zh': legacy, 'en': tmp_path / 'missing.en.toml'},
    )
    return tmp_path


def test_migrate_only_writes_diff(_temp_paths: Path) -> None:
    migrate_messages.migrate_legacy_messages()
    override = (_temp_paths / 'Locales' / 'Messages.zh.toml').read_text('Utf-8')
    # 与默认层不同的键被写入
    assert '玩家 {player} 上线啦！' in override
    # 未出现在旧文件中的键不写入
    assert 'player_quit' not in override


def test_migrate_is_idempotent(_temp_paths: Path) -> None:
    migrate_messages.migrate_legacy_messages()
    first = (_temp_paths / 'Locales' / 'Messages.zh.toml').read_text('Utf-8')
    migrate_messages.migrate_legacy_messages()
    assert (_temp_paths / 'Locales' / 'Messages.zh.toml').read_text('Utf-8') == first


def test_migrate_skips_when_no_legacy(monkeypatch, tmp_path: Path) -> None:
    locales_dir = tmp_path / 'Locales'
    monkeypatch.setattr(migrate_messages, 'LOCALES_DIR', locales_dir)
    monkeypatch.setattr(migrate_messages, 'MIGRATION_MARKER_PATH', locales_dir / '.migrated')
    monkeypatch.setattr(migrate_messages, 'MESSAGE_PATHS', {'zh': locales_dir / 'Messages.zh.toml'})
    monkeypatch.setattr(migrate_messages, 'LEGACY_MESSAGE_PATHS', {'zh': tmp_path / 'none.zh.toml'})
    migrate_messages.migrate_legacy_messages()
    assert not (locales_dir / 'Messages.zh.toml').exists()
