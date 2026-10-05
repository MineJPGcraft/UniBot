"""配置工具函数测试：deep_merge / sanitize_none。"""

from Core.Web.Routers.Config.Helpers import deep_merge, sanitize_none


def test_deep_merge():
    """深合并：嵌套字典递归合并，标量覆盖。"""
    base = {'a': 1, 'nested': {'x': 1, 'y': 2}}
    override = {'nested': {'y': 3}, 'b': 2}
    assert deep_merge(base, override) == {'a': 1, 'nested': {'x': 1, 'y': 3}, 'b': 2}


def test_sanitize_none():
    """None 值替换为空字符串，嵌套字典递归处理。"""
    data = {'a': None, 'nested': {'b': None, 'c': 1}}
    assert sanitize_none(data) == {'a': '', 'nested': {'b': '', 'c': 1}}
