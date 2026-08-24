"""WebUI 数据持久化测试（含已注销 refresh_token 存储）。"""

import asyncio

from Scripts.Api.Managers.Data import DataManager


def _manager(tmp_path) -> DataManager:
    """构建指向临时目录的管理器实例，避免触碰真实数据文件。"""
    manager = DataManager()
    manager.data_dir = tmp_path
    manager.users_file = tmp_path / 'Users.json'
    manager.secret_file = tmp_path / 'Secret.key'
    return manager


def test_revoke_persists_across_reload(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.load()
    asyncio.run(manager.revoke_refresh_token('token-1', 99999999999.0))
    reloaded = _manager(tmp_path)
    reloaded.load()
    assert reloaded.is_refresh_token_revoked('token-1')


def test_purge_expired_revocations_on_check(tmp_path) -> None:
    manager = _manager(tmp_path)
    manager.load()
    asyncio.run(manager.revoke_refresh_token('expired', 1.0))
    asyncio.run(manager.revoke_refresh_token('valid', 99999999999.0))
    assert not manager.is_refresh_token_revoked('expired')
    assert manager.is_refresh_token_revoked('valid')
