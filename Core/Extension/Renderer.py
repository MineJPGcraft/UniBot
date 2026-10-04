"""
渲染引擎基类、模板/资源注册表与统一渲染编排入口。

分层模型（见 Plan.md）：
- `renderer` 扩展：提供 HTML+CSS -> PNG 的渲染引擎（如 html2pic）。
- `template` 扩展：无代码扩展包，含 Jinja2 模板目录与受限配置 schema
  （`[template].config_schema`），配置经 `ExtensionConfigStore` 独立存储，
  在模板中以 `config.xxx` 访问。
- `resources` 扩展：无代码扩展包，提供模板可引用的静态资源根目录。

`RendererManager.render_image()` 是唯一渲染入口：选择模板候选（`config.image.template`
→ 默认模板回退）-> 为模板协商渲染引擎 -> 构建 Jinja2 环境 -> 注入模板配置与资源
函数 -> 渲染 HTML/CSS -> 委托渲染引擎输出 PNG 字节。运行时管理器见
`Runtime/Managers/Renderer.py`，本模块只保留扩展作者需要继承的 `BaseRenderer`
与模板上下文相关的定义（资源包装、上下文转义、注册记录）。
"""

from __future__ import annotations

import html
import json
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .Storage import ExtensionConfigStore

# 模板根目录（UniBot/Resources），默认字体所在处
RESOURCES_DIR = Path(__file__).parent.parent.parent / 'Resources'
FONT_PATH: Path = RESOURCES_DIR / 'Font.ttf'

# 支持的图片扩展名
_IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
# 单次资源读取上限（2 MiB）
_RESOURCE_MAX_BYTES = 2 * 1024 * 1024

# 保留名称：模板上下文保留名称，调用方不得覆盖
_RESERVED_CONTEXT_KEYS = {
    'config',
    'width',
    'height',
    'font_uri',
    'random',
    'resource_path',
    'resource_url',
    'resource_text',
    'resource_bytes',
}


def encode_context(context: dict) -> dict:
    """对模板上下文做 JSON 编码 + HTML 转义，防止注入。"""
    return json.loads(html.escape(json.dumps(context), False))


class _ReadOnlyConfig:
    """模板配置的只读点号访问包装（禁止模板修改 config）。"""

    def __init__(self, data: dict) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in self._data:
            raise AttributeError(name)
        return _wrap_readonly(self._data[name])

    def __getitem__(self, key: str) -> Any:
        return _wrap_readonly(self._data[key])

    def __repr__(self) -> str:
        return f'<config {self._data!r}>'


def _wrap_readonly(value: Any) -> Any:
    """递归包装 dict/list 为只读访问结构。"""
    if isinstance(value, dict):
        return _ReadOnlyConfig(value)
    if isinstance(value, list):
        return [_wrap_readonly(item) for item in value]
    return value


@dataclass(frozen=True)
class TemplateRegistration:
    """template 无代码扩展的注册记录。"""

    extension_id: str  # 与清单 id 一致，也是 config_store 的存储 id
    templates_dir: Path  # [template].entry 解析出的模板根目录
    resource_ids: tuple[str, ...]  # [template].resources 声明的资源扩展 id
    config_model: type[BaseModel]  # 由 config_schema 编译的受限 Pydantic 模型
    config_store: ExtensionConfigStore  # 独立配置存储（Config/Extensions/<id>.toml）
    support_renders: tuple[str, ...] = ()  # [template].support_renders 声明的渲染引擎 name（['*'] = 全部）


@dataclass(frozen=True)
class OnlineAsset:
    """在线资源包装：扩展在上下文中用它标记在线 URL，由渲染器决定如何引用。"""

    url: str

    def __str__(self) -> str:
        """按当前渲染器转换为可用字符串（未激活渲染器时原样返回 URL）。"""
        return _resolve_asset_str(self)


@dataclass(frozen=True)
class FileAsset:
    """本地文件资源包装：扩展在上下文中用它标记本地文件，由渲染器决定如何引用。"""

    path: Path

    def __str__(self) -> str:
        """按当前渲染器转换为可用字符串（未激活渲染器时返回磁盘路径）。"""
        return _resolve_asset_str(self)


# 当前渲染中的激活渲染器（供 Jinja2 资源函数把包装转换为渲染器可用字符串）。
# 用 ContextVar 而非模块级变量：并发渲染时各任务上下文隔离，避免互相覆盖
_current_renderer: ContextVar[BaseRenderer | None] = ContextVar('current_renderer', default=None)


def _resolve_asset_str(asset: OnlineAsset | FileAsset) -> str:
    """把资源包装按当前激活渲染器转换为字符串。"""
    renderer = _current_renderer.get()
    if isinstance(asset, OnlineAsset):
        return asset.url if renderer is None else renderer.deal_online_asset(asset)
    if isinstance(asset, FileAsset):
        return str(asset.path) if renderer is None else renderer.deal_file_asset(asset)
    return str(asset)


class BaseRenderer:
    """渲染引擎基类，所有渲染扩展必须实现。"""

    name: str = ''

    async def setup(self) -> None:
        """初始化（启动浏览器/加载资源等）。"""

    async def render(self, html_content: str, css: str, size: tuple[int, int] | None = None) -> bytes:
        """渲染为 PNG 字节。

        size: (宽度, 高度)；高度为 0/None 表示按内容自适应。
        """
        raise NotImplementedError

    async def shutdown(self) -> None:
        """清理资源。"""

    def deal_online_asset(self, asset: OnlineAsset) -> str:
        """把在线资源包装转换为本渲染器可用的字符串（默认原样返回 URL）。"""
        return asset.url

    def deal_file_asset(self, asset: FileAsset) -> str:
        """把本地文件包装转换为本渲染器可用的字符串（默认返回磁盘路径）。"""
        return str(asset.path)
