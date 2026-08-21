"""
扩展市场模型与安全解压工具。

市场扩展从 GitHub Release 以源码 zip 分发（不走 PyPI）。本模块提供：
- 注册表条目模型（`MarketExtension` / `MarketRelease`）
- 安装状态模型（`ExtensionInstallState`，写入 `States.toml`）
- 市场扩展包解压与清单读取（安全解压复用 `Scripts.Utils.safe_extract_zip`）。
"""

from pathlib import Path

from pydantic import BaseModel, Field

from Scripts.Utils import ArchiveError, safe_extract_zip

from .Base import ExtensionManifest, parse_manifest
from .Errors import ManifestError


class MarketRelease(BaseModel):
    """注册表中的单个版本发布条目。"""

    version: str = Field(min_length=1)
    asset_url: str = Field(min_length=1)
    sha256: str = ''
    unibot_version: str = '*'


class MarketExtension(BaseModel):
    """扩展注册表中收录的扩展条目。"""

    id: str = Field(min_length=1, pattern=r'^[A-Za-z0-9_]+$')
    name: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    description: str = ''
    official: bool = False
    releases: list[MarketRelease] = []

    def latest_release(self) -> MarketRelease | None:
        """返回最新版本发布条目（按 releases 顺序取最后一个）。"""
        return self.releases[-1] if self.releases else None


class ExtensionInstallState(BaseModel):
    """扩展安装状态（统一存放于 `Data/Extension/States.toml`，仅由框架维护）。"""

    source: str = 'local'  # 来源：local / market
    version: str = ''
    sha256: str = ''
    installed_at: str = ''
    repo: str = ''  # 市场来源仓库（owner/repo）
    python_dependencies: list[str] = []


# ===== 解压 + 清单读取 =====


def extract_market_package(archive_data: bytes, target_dir: Path) -> ExtensionManifest:
    """安全解压市场扩展包并读取其清单，返回清单信息。"""
    try:
        safe_extract_zip(archive_data, target_dir)
    except ArchiveError as error:
        raise ManifestError(str(error)) from error
    return _read_manifest_from_dir(target_dir)


def _read_manifest_from_dir(target_dir: Path) -> ExtensionManifest:
    """从解压目录读取并解析 Extension.toml。"""
    manifest_files = [path for path in target_dir.rglob('Extension.toml')]
    if not manifest_files:
        raise ManifestError('Extension package is missing the Extension.toml manifest!')
    manifest_path = manifest_files[0]
    relative = manifest_path.relative_to(target_dir)
    # 清单必须位于包根目录（根级 Extension.toml 或 <id>/Extension.toml），
    # 不允许嵌套在更深层级
    if len(relative.parts) > 2:
        raise ManifestError('Extension.toml must be located at the extension package root!')
    try:
        return parse_manifest(manifest_path.read_text('Utf-8'))
    except Exception as error:
        raise ManifestError(f'Failed to parse extension package manifest: {error}') from error
