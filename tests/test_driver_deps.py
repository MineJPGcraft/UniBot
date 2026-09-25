"""
适配器驱动依赖测试。

依赖写入的唯一通道是任务中心的 uv 命令：
`Driver.merge_driver` / `shrink_driver` 只维护 `.env` 的 DRIVER 字段，
新增驱动对应的底层依赖包（httpx / websockets 等）由调用方取
`Driver.driver_packages(added)` 交给 `uv add` 写入 `project.dependencies`。
"""

import pytest

from Scripts.Api.Config import Driver
from Scripts.Api.Config.Driver import BASE_DRIVER, driver_packages, get_driver_package, merge_driver, shrink_driver


class FakeConfigManager:
    """模拟 ConfigManager 的 .env 读写接口（仅 DRIVER 字段）。"""

    def __init__(self) -> None:
        self.environment = {'DRIVER': '~fastapi'}

    def update_env(self, new: dict) -> None:
        self.environment.update(new)


@pytest.fixture()
def fake_manager(monkeypatch):
    """用假 ConfigManager 替换 Driver 模块内的依赖。"""
    fake = FakeConfigManager()
    monkeypatch.setattr(Driver, 'config_manager', fake)
    return fake


def test_merge_driver_updates_env_and_reports_added(fake_manager):
    """合并驱动时只写 .env 的 DRIVER，并回报新增驱动供调用方走 uv add。"""
    new_driver, added = merge_driver(['~httpx', '~websockets'])

    assert new_driver == '~fastapi+~httpx+~websockets'
    assert added == ['~httpx', '~websockets']
    assert fake_manager.environment['DRIVER'] == '~fastapi+~httpx+~websockets'
    # 依赖包不再由本函数写入，改由 driver_packages(added) 交给 uv add
    assert driver_packages(added) == ['httpx', 'websockets']


def test_merge_driver_does_not_rewrite_pyproject(fake_manager):
    """merge_driver 不再触碰 pyproject.toml（写入只能经 uv 命令）。"""
    fake_manager.read_pyproject = None  # 若被调用会抛 TypeError

    merge_driver(['~httpx'])

    assert fake_manager.environment['DRIVER'] == '~fastapi+~httpx'


def test_merge_driver_skips_already_present(fake_manager):
    """已存在的驱动不重复追加，返回空增量。"""
    fake_manager.environment = {'DRIVER': '~fastapi+~httpx'}

    new_driver, added = merge_driver(['~httpx'])

    assert new_driver == '~fastapi+~httpx'
    assert added == []


def test_merge_driver_skips_base_driver(fake_manager):
    """BASE_DRIVER（~fastapi）无需显式声明依赖，不产出待装包。"""
    _, added = merge_driver(['~fastapi'])

    assert added == []
    assert driver_packages([BASE_DRIVER]) == []


def test_shrink_driver_removes_driver_only(fake_manager):
    """收缩驱动时只更新 DRIVER，不产出待卸载包（避免误删被复用的底层包）。"""
    fake_manager.environment = {'DRIVER': '~fastapi+~websockets'}

    new_driver, removed = shrink_driver(['~websockets'])

    assert new_driver == '~fastapi'
    assert removed == ['~websockets']
    assert fake_manager.environment['DRIVER'] == '~fastapi'


def test_shrink_driver_keeps_base_driver(fake_manager):
    """移除驱动后 BASE_DRIVER 仍被保留。"""
    fake_manager.environment = {'DRIVER': '~fastapi+~httpx+~websockets'}

    new_driver, _ = shrink_driver(['~httpx', '~websockets'])

    assert new_driver == '~fastapi'


def test_shrink_driver_ignores_absent_driver(fake_manager):
    """移除不在 DRIVER 中的驱动时返回空增量。"""
    new_driver, removed = shrink_driver(['~websockets'])

    assert new_driver == '~fastapi'
    assert removed == []


def test_driver_packages_deduplicates():
    """同一底层包被多个驱动映射时只返回一次。"""
    assert driver_packages(['~httpx', '~httpx']) == ['httpx']


def test_get_driver_package_mapping():
    """驱动标记到底层包的映射完整。"""
    assert get_driver_package('~websockets') == 'websockets'
    assert get_driver_package('~httpx') == 'httpx'
    assert get_driver_package('~aiohttp') == 'aiohttp'
    assert get_driver_package('~quart') == 'quart'
    assert get_driver_package('~fastapi') is None
