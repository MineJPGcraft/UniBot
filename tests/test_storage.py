"""存储测试：独立数据边界、路径越界、原子写、State.toml 保护（验证点 15、16）。"""

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, Field

from Core.Extension import (
    RESERVED_STATE_FILE,
    ExtensionConfigStore,
    ExtensionDataStore,
    StorageError,
)


class SampleConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    api_key: str = Field(default='', description='key')
    city: str = Field(default='Shanghai', min_length=1)


class EmptyConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')


@pytest.fixture
def config_root(tmp_path: Path) -> Path:
    return tmp_path / 'Config' / 'Extensions'


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    return tmp_path / 'Data' / 'Exs' / 'WeatherExt'


# ===== ExtensionConfigStore =====


class TestConfigStore:
    def test_update_and_value_roundtrip(self, config_root: Path):
        store = ExtensionConfigStore(config_root, 'WeatherExt', SampleConfig)
        updated = store.update({'api_key': 'abc', 'city': 'Beijing'})
        assert updated.api_key == 'abc'
        assert updated.city == 'Beijing'
        # 重新构造 store 从磁盘读取，验证持久化
        reloaded = ExtensionConfigStore(config_root, 'WeatherExt', SampleConfig)
        assert reloaded.value.api_key == 'abc'
        assert reloaded.value.city == 'Beijing'

    def test_load_missing_uses_defaults(self, config_root: Path):
        store = ExtensionConfigStore(config_root, 'Other', SampleConfig)
        assert store.value.api_key == ''
        assert store.value.city == 'Shanghai'

    def test_load_missing_creates_default_file(self, config_root: Path):
        ExtensionConfigStore(config_root, 'WeatherExt', SampleConfig)
        assert (config_root / 'WeatherExt.toml').exists()

    def test_no_fields_skips_config_file(self, config_root: Path):
        """无配置字段的扩展不创建配置文件，并清理历史遗留空文件。"""
        legacy = config_root / 'About.toml'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text('', encoding='Utf-8')
        store = ExtensionConfigStore(config_root, 'About', EmptyConfig)
        assert store.value == EmptyConfig()
        assert not legacy.exists()
        assert not (config_root / 'About.toml').exists()
        assert not (config_root / 'Command.toml').exists()

    def test_unknown_field_rejected_on_load(self, config_root: Path):
        # 手动写入未知字段
        config_root.mkdir(parents=True, exist_ok=True)
        config_file = config_root / 'WeatherExt.toml'
        config_file.write_text('api_key = "x"\nunknown = 1\n', encoding='Utf-8')
        with pytest.raises(Exception):
            ExtensionConfigStore(config_root, 'WeatherExt', SampleConfig)

    def test_update_invalid_keeps_original(self, config_root: Path):
        store = ExtensionConfigStore(config_root, 'WeatherExt', SampleConfig)
        store.update({'api_key': 'abc', 'city': 'Beijing'})
        with pytest.raises(Exception):
            store.update({'city': ''})  # 空城市违反 min_length
        assert store.value.city == 'Beijing'


# ===== ExtensionDataStore =====


class TestDataStore:
    def test_write_and_read_text(self, data_root: Path):
        store = ExtensionDataStore(data_root)
        store.write_text('notes.txt', 'hello')
        assert store.read_text('notes.txt') == 'hello'

    def test_write_and_read_json(self, data_root: Path):
        store = ExtensionDataStore(data_root)
        store.write_json('data.json', {'a': 1})
        assert store.read_json('data.json') == {'a': 1}

    def test_absolute_path_rejected(self, data_root: Path):
        store = ExtensionDataStore(data_root)
        with pytest.raises(StorageError):
            store.read_text('/etc/passwd')

    def test_parent_traversal_rejected(self, data_root: Path):
        store = ExtensionDataStore(data_root)
        with pytest.raises(StorageError):
            store.read_text('../secret.txt')

    def test_state_file_access_rejected(self, data_root: Path):
        store = ExtensionDataStore(data_root)
        with pytest.raises(StorageError):
            store.read_text(RESERVED_STATE_FILE)
