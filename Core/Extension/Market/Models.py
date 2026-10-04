"""扩展市场数据模型：注册表条目、安装状态与市场视图对象。

市场扩展从 GitHub Release 以源码 zip 分发（不走 PyPI）。本模块只定义**数据形状**
（注册表 Pydantic 模型、安装状态与安装/卸载结果 dataclass），不包含网络、磁盘或解压
行为——那些属于 `Manager.py` 的安装管线。市场列表/版本列表的展示字典由 `Manager.py`
按职责直接产出，避免多一层无谓的 DTO 搬运。
"""

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from ..Manifest import is_unibot_compatible

# ===== 注册表条目 =====


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

    def compatible_release(self) -> MarketRelease | None:
        """返回兼容当前 UniBot 版本的最新发布条目，无兼容版本时返回 None。"""
        for release in reversed(self.releases):
            if is_unibot_compatible(release.unibot_version):
                return release
        return None

    def find_release(self, version: str) -> MarketRelease | None:
        """按版本号查找发布条目，不存在返回 None。"""
        return next((release for release in self.releases if release.version == version), None)


class ExtensionInstallState(BaseModel):
    """扩展安装状态（统一存放于 `Data/Extension/States.toml`，仅由框架维护）。"""

    source: str = 'local'  # 来源：local / market
    version: str = ''
    sha256: str = ''
    installed_at: str = ''
    repo: str = ''  # 市场来源仓库（owner/repo）
    python_dependencies: list[str] = []


# ===== 安装/卸载结果 =====


@dataclass(slots=True)
class MarketOperationResult:
    """市场操作（安装/卸载）统一结果（msg_key / msg_params 供 WebUI 按界面语言翻译）。"""

    success: bool
    msg_key: str
    msg_params: dict = field(default_factory=dict)
    version: str = ''
    warning_key: str = ''
    warning_params: dict = field(default_factory=dict)
    error: str = ''
