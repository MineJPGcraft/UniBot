"""配置相关的纯函数工具。"""

from copy import deepcopy


def deep_merge(base: dict, override: dict) -> dict:
    """递归深合并两个字典，override 中的值覆盖 base。"""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
            continue
        result[key] = deepcopy(value)
    return result


def sanitize_none(data: dict) -> dict:
    """递归替换 None 值为空字符串（tomlkit 不支持 None 值）。"""
    result = {}
    for key, value in data.items():
        if value is None:
            result[key] = ''
            continue
        if isinstance(value, dict):
            result[key] = sanitize_none(value)
            continue
        result[key] = value
    return result
