"""
语言包目录模型：嵌套字典 + 点路径查找 + 深合并。

语言包以「点路径即嵌套段」的 TOML 表达（如 `[core.events]` 对应 `core.events.*`）。
Catalog 提供 `merge`（默认层叠加）与 `lookup`（点路径取字符串叶子）。
"""

from __future__ import annotations

from typing import Any


class Catalog:
    """单个语言的嵌套翻译表，支持点路径访问与深合并。"""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data or {}

    @property
    def data(self) -> dict[str, Any]:
        """返回底层嵌套字典（只读用途）。"""
        return self._data

    def merge(self, other: dict[str, Any]) -> None:
        """把另一份嵌套表深合并进本表（同键以 other 覆盖，即最后写入者优先）。"""
        self._data = _deep_merge(self._data, other)

    def contains(self, key: str) -> bool:
        """判断点路径键是否存在且为叶子。"""
        try:
            self._lookup(key)
        except KeyError:
            return False
        return True

    def lookup(self, key: str) -> str:
        """按点路径取字符串叶子，缺失或非字符串时抛 KeyError。"""
        value = self._lookup(key)
        if not isinstance(value, str):
            raise KeyError(key)
        return value

    def lookup_value(self, key: str) -> Any:
        """按点路径取任意叶子值（字符串或字符串列表），缺失时抛 KeyError。"""
        value = self._lookup(key)
        if not isinstance(value, (str, list)):
            raise KeyError(key)
        return value

    def _lookup(self, key: str) -> Any:
        node: Any = self._data
        for part in key.split('.'):
            if not isinstance(node, dict) or part not in node:
                raise KeyError(key)
            node = node[part]
        return node

    def flattened(self) -> dict[str, Any]:
        """展平为「点路径 → 叶子值」映射（字符串与字符串列表；非叶子被跳过）。"""
        return _flatten(self._data)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """递归合并两个嵌套字典，overlay 优先。"""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
            continue
        result[key] = value
    return result


def _flatten(data: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    """递归展平嵌套字典为点路径映射（字符串与字符串列表均视为叶子）。"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, path))
        elif _is_leaf(value):
            result[path] = value
    return result


def _is_leaf(value: Any) -> bool:
    """字符串，或全为字符串的列表，视为可展示叶子。"""
    if isinstance(value, str):
        return True
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
