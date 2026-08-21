from pathlib import Path
from typing import Any

import tomlkit


class MessageGroup:
    """
    嵌套消息表，支持 messages.<表>.<子表>.<键> 链式访问消息文本
        占位符使用 Python str.format 语法，如 messages.xxx.yyy.format(player='Steve')。
    """

    __slots__ = ('_data',)

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            raise AttributeError(key)
        if key not in self._data:
            raise AttributeError(f'Message [{key}] is missing from Messages.toml!')
        value = self._data[key]
        if isinstance(value, dict):
            return MessageGroup(value)
        if isinstance(value, (str, list)):
            return value
        raise TypeError(f'[{key}] in Messages.toml should be a string or a list of strings!')


MESSAGES_TOML_PATH = Path('Config') / 'Messages.toml'


def load_messages() -> MessageGroup:
    """从 Messages.toml 加载消息配置，文件缺失则抛错。"""
    if not MESSAGES_TOML_PATH.exists():
        raise FileNotFoundError(
            f'Message config file {MESSAGES_TOML_PATH} does not exist, please create it and fill in as needed!'
        )
    toml_data = tomlkit.parse(MESSAGES_TOML_PATH.read_text('Utf-8'))
    return MessageGroup(dict(toml_data))


def reload_messages() -> None:
    """重新加载消息配置，供保存后热更新。"""

    global messages

    messages = load_messages()


messages = load_messages()
