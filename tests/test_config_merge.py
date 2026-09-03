"""Config.toml 合并优先级测试。

验证 _merge_toml 的优先级语义：Config.toml > .env / 环境变量 > 模型默认值。
重点回归：系统环境变量（如 Debian 的 LANGUAGE）不得污染 Config.toml 中显式
设置的自定义字段（如 language），否则会在合并前触发校验崩溃。
"""

import pytest

from Scripts.Config import Config, _merge_toml


def test_toml_overrides_environment_variable(monkeypatch):
    """Config.toml 中显式设置的字段应覆盖同名环境变量。"""
    monkeypatch.setenv('LANGUAGE', 'en_US')
    merged = _merge_toml('language = "zh"\n')
    assert merged['language'] == 'zh'
    assert Config.model_validate(merged).language == 'zh'


def test_environment_variable_does_not_pollute_custom_field(monkeypatch):
    """未在 Config.toml 中设置的自定义字段，不应被系统环境变量污染。"""
    monkeypatch.setenv('LANGUAGE', 'en_US')
    # Config.toml 未写 language，应回退到模型默认值 zh，而不是环境变量的 en_US
    merged = _merge_toml('')
    assert Config.model_validate(merged).language == 'zh'


def test_nonebot_framework_field_keeps_env_source():
    """NoneBot 框架字段（来自 get_driver().config）保留在合并结果中。"""
    from nonebot import get_driver

    driver_config = get_driver().config.model_dump()
    merged = _merge_toml('')
    # 框架字段应原样保留（无论其值来自 .env 还是默认值）
    for field_name in ('port', 'superusers', 'command_start'):
        assert merged[field_name] == driver_config[field_name]


def test_toml_overrides_nonebot_framework_field():
    """Config.toml 显式设置时，也可覆盖 NoneBot 框架字段。"""
    merged = _merge_toml('port = 8001\n')
    assert merged['port'] == 8001
    assert Config.model_validate(merged).port == 8001


def test_invalid_language_still_rejected(monkeypatch):
    """非法 language 值仍应被校验拒绝（不因环境变量而绕过）。"""
    monkeypatch.setenv('LANGUAGE', 'en_US')
    with pytest.raises(ValueError):
        Config.model_validate(_merge_toml('language = "fr"\n'))