"""
A8 市场安全解压与安装事务测试。

验证方案 item 19：SHA-256 不匹配、清单不一致、路径穿越、符号链接、超出文件限制时，
当前扩展版本不发生改变。
"""

import hashlib
import io
import zipfile

import pytest

from Scripts.Extensions import (
    ManifestError,
    MarketExtension,
    MarketRelease,
    extract_market_package,
    is_unibot_compatible,
)
from Scripts.Extensions.MarketManager import ExtensionMarketManager
from Scripts.Utils import MAX_ARCHIVE_FILES, ArchiveError, safe_extract_zip


def _make_zip(files: dict[str, bytes]) -> bytes:
    """生成内存 zip（files: 相对路径 -> 内容）。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def _valid_manifest() -> str:
    """生成一份合法的 Extension.toml 内容。"""
    return """
[manifest]
schema_version = 1

[extension]
id = "TestExt"
name = "测试扩展"
version = "1.0.0"
author = "UniBot"
description = "测试"
types = ["api"]

[compatibility]
unibot = "*"

[dependencies]
extensions = []
python = []
"""


# ===== 安全解压 =====


class TestSafeExtractZip:
    def test_extract_plain(self, tmp_path):
        archive = _make_zip({'TestExt/__init__.py': b'print(1)'})
        safe_extract_zip(archive, tmp_path)
        assert (tmp_path / 'TestExt' / '__init__.py').read_bytes() == b'print(1)'

    def test_path_traversal_rejected(self, tmp_path):
        archive = _make_zip({'../evil.py': b'evil'})
        with pytest.raises(ArchiveError):
            safe_extract_zip(archive, tmp_path)
        # 不得写出目标目录
        assert not (tmp_path.parent / 'evil.py').exists()

    def test_absolute_path_rejected(self, tmp_path):
        archive = _make_zip({'/abs.py': b'evil'})
        with pytest.raises(ArchiveError):
            safe_extract_zip(archive, tmp_path)

    def test_symlink_rejected(self, tmp_path):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            info = zipfile.ZipInfo('link')
            # 在 Unix 标志位中标记为符号链接
            info.external_attr = 0o120777 << 16
            zf.writestr(info, b'target')
        with pytest.raises(ArchiveError):
            safe_extract_zip(buffer.getvalue(), tmp_path)

    def test_not_zip_rejected(self, tmp_path):
        with pytest.raises(ArchiveError):
            safe_extract_zip(b'not a zip', tmp_path)

    def test_too_many_files_rejected(self, tmp_path):
        files = {f'f{i}': b'x' for i in range(MAX_ARCHIVE_FILES + 1)}
        archive = _make_zip(files)
        with pytest.raises(ArchiveError):
            safe_extract_zip(archive, tmp_path)

    def test_too_large_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr('Scripts.Utils.MAX_ARCHIVE_TOTAL', 10)
        archive = _make_zip({'big.bin': b'x' * 100})
        with pytest.raises(ArchiveError):
            safe_extract_zip(archive, tmp_path)


# ===== 解压 + 清单读取 =====


class TestExtractMarketPackage:
    def test_extract_with_manifest(self, tmp_path):
        archive = _make_zip(
            {
                'TestExt/Extension.toml': _valid_manifest().encode(),
                'TestExt/__init__.py': b'pass',
            }
        )
        manifest = extract_market_package(archive, tmp_path)
        assert manifest.extension.id == 'TestExt'
        assert (tmp_path / 'TestExt' / '__init__.py').exists()

    def test_missing_manifest_rejected(self, tmp_path):
        archive = _make_zip({'TestExt/__init__.py': b'pass'})
        with pytest.raises(ManifestError):
            extract_market_package(archive, tmp_path)

    def test_manifest_not_at_root_rejected(self, tmp_path):
        archive = _make_zip(
            {
                'TestExt/sub/Extension.toml': _valid_manifest().encode(),
            }
        )
        with pytest.raises(ManifestError):
            extract_market_package(archive, tmp_path)

    def test_invalid_manifest_rejected(self, tmp_path):
        archive = _make_zip({'TestExt/Extension.toml': b'not toml [[['})
        with pytest.raises(ManifestError):
            extract_market_package(archive, tmp_path)


# ===== SHA-256 =====


def test_sha256_mismatch_rejected(monkeypatch):
    """SHA-256 与下载内容不匹配时抛 ManifestError。"""
    from Scripts.Extensions.MarketManager import ExtensionMarketManager

    manager = ExtensionMarketManager()
    archive = _make_zip({'TestExt/__init__.py': b'pass'})

    async def fake_download(url):
        return io.BytesIO(archive)

    async def run():
        return await manager._download_release('https://example.com/x.zip', hashlib.sha256(b'wrong').hexdigest())

    monkeypatch.setattr('Scripts.Extensions.MarketManager.github_download', fake_download)
    with pytest.raises(ManifestError):
        import asyncio

        asyncio.run(run())


def test_sha256_match_ok(monkeypatch):
    """SHA-256 匹配时下载成功。"""
    from Scripts.Extensions.MarketManager import ExtensionMarketManager

    manager = ExtensionMarketManager()
    archive = _make_zip({'TestExt/__init__.py': b'pass'})

    async def fake_download(url):
        return io.BytesIO(archive)

    async def run():
        return await manager._download_release('https://example.com/x.zip', hashlib.sha256(archive).hexdigest())

    monkeypatch.setattr('Scripts.Extensions.MarketManager.github_download', fake_download)
    import asyncio

    result = asyncio.run(run())
    assert result == archive


# ===== 多版本兼容选择 =====


def _patch_unibot_version(monkeypatch, version: str = '1.0.2') -> None:
    """打桩当前 UniBot 版本：Base 内部判定与 MarketManager 直接引用都要覆盖。"""
    monkeypatch.setattr('Scripts.Extensions.Base.get_unibot_version', lambda: version)
    monkeypatch.setattr('Scripts.Extensions.MarketManager.get_unibot_version', lambda: version)


def _market_extension(*releases: tuple[str, str]) -> MarketExtension:
    """构造市场扩展条目（releases 为 (版本, unibot 约束) 列表，按传入顺序升序）。"""
    return MarketExtension(
        id='TestExt',
        name='测试扩展',
        repo='owner/TestExt',
        releases=[
            MarketRelease(version=version, asset_url=f'https://example.com/{version}.zip', unibot_version=constraint)
            for version, constraint in releases
        ],
    )


class TestVersionCompatibility:
    """兼容判定与历史版本回退：仅在当前核心版本内挑选发布。"""

    def test_is_unibot_compatible(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        assert is_unibot_compatible('*')
        assert is_unibot_compatible('')
        assert is_unibot_compatible('>=1.0.0')
        assert is_unibot_compatible('>= 1.0.2')
        assert not is_unibot_compatible('>=9.0.0')
        # 非法约束视为不兼容，不抛错
        assert not is_unibot_compatible('not-a-specifier')

    def test_compatible_release_prefers_latest_compatible(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        entry = _market_extension(('1.0.0', '*'), ('1.0.1', '>=9.0.0'), ('1.0.2', '>=9.0.0'))
        assert entry.latest_release().version == '1.0.2'
        # 新版本都不兼容 → 回退到最新的历史兼容版本
        assert entry.compatible_release().version == '1.0.0'

    def test_compatible_release_returns_none_without_compatible(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        entry = _market_extension(('1.0.0', '>=9.0.0'), ('1.0.1', '>=9.0.0'))
        assert entry.compatible_release() is None

    def test_select_release_defaults_to_compatible(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        entry = _market_extension(('1.0.0', '*'), ('1.0.1', '>=9.0.0'))
        release, error_key = ExtensionMarketManager._select_release(entry, '')
        assert error_key == ''
        assert release.version == '1.0.0'

    def test_select_release_unsupported(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        entry = _market_extension(('1.0.0', '>=9.0.0'))
        release, error_key = ExtensionMarketManager._select_release(entry, '')
        assert release is None
        assert error_key == 'extensions.unsupported_version'

    def test_select_release_explicit_version_allows_incompatible(self, monkeypatch):
        """显式指定版本时按版本号安装（用于回退到历史版本），不校验兼容性。"""
        _patch_unibot_version(monkeypatch)
        entry = _market_extension(('1.0.0', '*'), ('1.0.1', '>=9.0.0'))
        release, error_key = ExtensionMarketManager._select_release(entry, '1.0.1')
        assert error_key == ''
        assert release.version == '1.0.1'

    def test_select_release_unknown_version(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        entry = _market_extension(('1.0.0', '*'))
        release, error_key = ExtensionMarketManager._select_release(entry, '9.9.9')
        assert release is None
        assert error_key == 'extensions.market_version_not_found'

    def test_get_releases_flags(self, monkeypatch, tmp_path):
        """版本清单按版本倒序，标记兼容性与已安装版本。"""
        _patch_unibot_version(monkeypatch)
        monkeypatch.setattr('Scripts.Extensions.MarketManager.STATES_ROOT', tmp_path / 'Extension')
        manager = ExtensionMarketManager()
        manager.market_cache = {'TestExt': _market_extension(('1.0.0', '*'), ('1.0.1', '>=9.0.0'))}
        options = manager.get_releases('TestExt')
        assert [item.version for item in options] == ['1.0.1', '1.0.0']
        assert options[0].compatible is False
        assert options[1].compatible is True
        assert not any(item.installed for item in options)
        assert manager.get_releases('Missing') == []

    def test_market_dicts_expose_compatible_target(self, monkeypatch):
        """市场列表暴露默认安装目标版本与回退标记，供 WebUI 展示。"""
        _patch_unibot_version(monkeypatch)
        manager = ExtensionMarketManager()
        manager.market_cache = {'TestExt': _market_extension(('1.0.0', '*'), ('1.0.1', '>=9.0.0'))}
        item = manager._market_dicts()[0]
        assert item['latest_version'] == '1.0.1'
        assert item['latest_compatible'] is False
        assert item['target_version'] == '1.0.0'
        assert item['compatible'] is True
        assert item['has_compatible_fallback'] is True
        assert item['unibot_version'] == '1.0.2'

    def test_market_dicts_flags_unsupported(self, monkeypatch):
        _patch_unibot_version(monkeypatch)
        manager = ExtensionMarketManager()
        manager.market_cache = {'TestExt': _market_extension(('1.0.0', '>=9.0.0'))}
        item = manager._market_dicts()[0]
        assert item['compatible'] is False
        assert item['target_version'] == '1.0.0'  # 无兼容版本时回退展示最新版（仅展示，安装会被拒绝）


class TestInstallVersionSelection:
    """安装流程：自动挑选兼容版本，不兼容时拒绝并返回可翻译的消息键。"""

    @staticmethod
    def _manager(monkeypatch, extension: MarketExtension) -> ExtensionMarketManager:
        _patch_unibot_version(monkeypatch)
        manager = ExtensionMarketManager()
        manager.market_cache = {extension.id: extension}

        async def fake_download(asset_url, expected_sha256):
            return b'archive'

        def fake_transaction(extension_id, archive_data, release):
            return True, 'ok'

        monkeypatch.setattr(manager, '_download_release', fake_download)
        monkeypatch.setattr(manager, '_install_transaction', fake_transaction)
        monkeypatch.setattr(manager, '_record_install', lambda *args: None)
        return manager

    def test_install_rejects_unsupported_without_download(self, monkeypatch):
        import asyncio

        manager = self._manager(monkeypatch, _market_extension(('1.0.0', '>=9.0.0')))
        result = asyncio.run(manager.install('TestExt'))
        assert result.success is False
        assert result.msg_key == 'extensions.unsupported_version'
        assert result.msg_params == {'id': 'TestExt', 'version': ''}

    def test_install_falls_back_and_reports_warning(self, monkeypatch):
        import asyncio

        manager = self._manager(monkeypatch, _market_extension(('1.0.0', '*'), ('1.0.1', '>=9.0.0')))
        result = asyncio.run(manager.install('TestExt'))
        assert result.success is True
        assert result.version == '1.0.0'
        assert result.msg_key == 'extensions.install_success'
        assert result.warning_key == 'extensions.install_compatible_fallback'
        assert result.warning_params['latest'] == '1.0.1'

    def test_install_latest_no_warning(self, monkeypatch):
        import asyncio

        manager = self._manager(monkeypatch, _market_extension(('1.0.0', '*'), ('1.0.1', '*')))
        result = asyncio.run(manager.install('TestExt'))
        assert result.success is True
        assert result.version == '1.0.1'
        assert result.warning_key == ''

    def test_install_unknown_extension(self, monkeypatch):
        import asyncio

        manager = self._manager(monkeypatch, _market_extension(('1.0.0', '*')))
        result = asyncio.run(manager.install('Missing'))
        assert result.success is False
        assert result.msg_key == 'extensions.market_not_found_in_cache'

    def test_install_failure_returns_reason_key(self, monkeypatch):
        import asyncio

        manager = self._manager(monkeypatch, _market_extension(('1.0.0', '*')))
        monkeypatch.setattr(manager, '_install_transaction', lambda *args: (False, 'boom'))
        result = asyncio.run(manager.install('TestExt'))
        assert result.success is False
        assert result.msg_key == 'extensions.install_failed_reason'
        assert result.error == 'boom'
