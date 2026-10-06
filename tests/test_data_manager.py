"""WebUI 数据持久化测试（含已注销 refresh_token 存储）。"""

import asyncio

from Core.Web.Managers.Data import DataManager


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


def test_corrupt_user_file_is_backed_up(tmp_path) -> None:
    """损坏的用户数据文件先备份再以空数据启动，不直接覆盖原文件。"""
    (tmp_path / 'Users.json').write_text('{not valid json', encoding='Utf-8')
    manager = _manager(tmp_path)
    manager.load()
    assert manager.users == {}
    backups = list(tmp_path.glob('Users.json.corrupt.*'))
    assert len(backups) == 1
    assert backups[0].read_text('Utf-8') == '{not valid json'


def test_concurrent_user_updates_keep_all_writes(tmp_path) -> None:
    """并发更新不丢字段：50 个并发创建用户全部落盘。"""

    async def run():
        manager = _manager(tmp_path)
        manager.load()
        await asyncio.gather(*(manager.create_user(f'user{index}', 'pw', f'nick{index}') for index in range(50)))
        return manager

    manager = asyncio.run(run())
    assert len(manager.users) == 50
    reloaded = _manager(tmp_path)
    reloaded.load()
    assert len(reloaded.users) == 50
