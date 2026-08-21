"""
扩展独立配置与数据存储工具。

每个扩展使用作用域受限的 `Config/Extensions/<id>.toml` 与 `Data/Exs/<id>/`，
拒绝绝对路径、`..` 越界、访问其它扩展目录及覆盖框架保留文件。
所有写操作默认原子提交，失败时保留旧文件；同实例的读写由实例锁串行化。

启停标志由用户编辑 `Config/Extensions.toml`；管理状态（启停、来源、版本等）
统一存放于 `Data/Extension/States.toml`（见 Loader 与 ExtensionManager）。
"""

import json
import tempfile
import threading
import tomllib
from pathlib import Path
from typing import Any, Generic, TypeVar

import tomlkit
from pydantic import BaseModel

from Scripts.Logging import logger

from .Errors import StorageError

# 框架保留文件，扩展不得写入
RESERVED_STATE_FILE = 'State.toml'
ConfigModelT = TypeVar('ConfigModelT', bound=BaseModel)


def _check_relative(relative: str) -> Path:
    """校验相对路径不越界、为绝对路径时拒绝，并返回规范化后的 Path。"""
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise StorageError(f'Disallowed path: {relative}')
    return path


def _atomic_write(file_path: Path, content: str | bytes) -> None:
    """使用临时文件与原子替换写入内容，失败时保留旧文件。"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    mode = 'wb' if isinstance(content, bytes) else 'w'
    try:
        with tempfile.NamedTemporaryFile(
            mode,
            encoding=None if isinstance(content, bytes) else 'Utf-8',
            dir=file_path.parent,
            suffix='.tmp',
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(file_path)
    except Exception as error:
        logger.error(f'Failed to write file: {file_path}! Error: {error}')
        raise StorageError(f'Failed to write file: {error}') from error


class ExtensionConfigStore(Generic[ConfigModelT]):
    """
    当前扩展独占的 Config.toml 读写工具。

        配置写入 `Config/Extensions/<id>.toml`（由 `root_dir` 指向该文件的父目录，
        文件名为 `id.toml`）。`value` 是经过校验的当前配置模型；`update(values)`
        再次校验并使用 `model_dump(mode='json')` 整体原子替换配置文件。校验或
        写盘失败时保留旧文件。所有读写通过实例锁串行化。
    """

    def __init__(self, root_dir: Path, extension_id: str, model: type[ConfigModelT]) -> None:
        self.root_dir = root_dir
        self.config_path = root_dir / f'{extension_id}.toml'
        self._model: type[ConfigModelT] = model
        self._lock = threading.RLock()
        self._value: ConfigModelT = self._load()

    def _load_text(self) -> str:
        """读取当前配置文件文本，文件缺失时视为空配置。"""
        if not self.config_path.exists():
            return ''
        return self.config_path.read_text('Utf-8')

    def _load(self) -> ConfigModelT:
        """读取配置并校验；文件缺失或为空时用默认值。仅当模型有字段才自动创建配置文件。"""
        with self._lock:
            if not self._model.model_fields:
                self.config_path.unlink(missing_ok=True)
                return self._model()
            content = self._load_text()
            if not content:
                model = self._model()
                self._save(model)
                return model
            try:
                data = tomllib.loads(content)
                return self._model.model_validate(data)
            except Exception as error:
                raise StorageError(f'Failed to load extension config: {error}') from error

    @property
    def value(self) -> ConfigModelT:
        """返回经过校验的当前配置模型。"""
        with self._lock:
            return self._value

    def update(self, values: dict) -> ConfigModelT:
        """校验并原子持久化配置；校验失败抛出异常且不修改原配置。"""
        with self._lock:
            updated = self._model.model_validate(values)
            self._save(updated)
            self._value = updated
            return updated

    def _save(self, model: ConfigModelT) -> None:
        """使用 model_dump(mode='json') 整体原子替换配置文件。"""
        content = tomlkit.dumps(model.model_dump(mode='json'))
        _atomic_write(self.config_path, content)


class ExtensionDataStore:
    """
    当前扩展独占的 Data/ 读写工具，所有路径经越界与保留文件检查；
        同实例的读写由实例锁串行化。
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self._lock = threading.RLock()

    def _resolve(self, relative: str) -> Path:
        """将相对路径解析为根目录内的安全绝对路径。"""
        normalized = _check_relative(relative)
        if normalized.name == RESERVED_STATE_FILE or RESERVED_STATE_FILE in normalized.parts:
            raise StorageError(f'Access to framework reserved file is not allowed: {RESERVED_STATE_FILE}')
        return self.root_dir / normalized

    def path(self, relative: str) -> Path:
        """返回根目录内安全解析后的路径（不保证存在）。"""
        return self._resolve(relative)

    def read_text(self, relative: str) -> str:
        """读取文本文件。"""
        with self._lock:
            return self._resolve(relative).read_text('Utf-8')

    def write_text(self, relative: str, content: str) -> None:
        """原子写入文本文件。"""
        with self._lock:
            _atomic_write(self._resolve(relative), content)

    def read_json(self, relative: str) -> Any:
        """读取 JSON 文件并解析。"""
        with self._lock:
            return json.loads(self._resolve(relative).read_text('Utf-8'))

    def write_json(self, relative: str, data: Any) -> None:
        """原子写入 JSON 文件。"""
        with self._lock:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            _atomic_write(self._resolve(relative), content)

    def read_bytes(self, relative: str) -> bytes:
        """读取字节文件。"""
        with self._lock:
            return self._resolve(relative).read_bytes()

    def write_bytes(self, relative: str, content: bytes) -> None:
        """原子写入字节文件。"""
        with self._lock:
            _atomic_write(self._resolve(relative), content)
