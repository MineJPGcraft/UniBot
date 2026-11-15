"""扩展运行记录与注册容器，生命周期编排由 `Runtime/Manager.py` 负责。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from Core.Logging import logger

from ...Extension import Extension, ExtensionState
from ...Manifest import ExtensionManifest, ExtensionMetadata


@dataclass
class ExtensionRecord:
    """持有扩展元数据及可选代码实例，无代码或未加载扩展独立保存状态。"""

    manifest: ExtensionManifest
    directory: Path
    single_file: bool
    enabled: bool
    metadata: ExtensionMetadata = field(init=False)
    builtin: bool = False
    module_path: str = ''
    blocked_reason: str = ''
    instance: Extension | None = None
    _state: ExtensionState = ExtensionState.discovered
    _failure_reason: str | None = None

    def __post_init__(self) -> None:
        self.metadata = ExtensionMetadata(self.manifest)

    def mark_state(self, state: ExtensionState, reason: str | None = None) -> None:
        """迁移未实例化扩展的状态并记录失败原因（实例存在时状态由实例自身持有）。"""
        self._state = state
        self._failure_reason = reason

    @property
    def state(self) -> ExtensionState:
        return self.instance.state if self.instance is not None else self._state

    @property
    def failure_reason(self) -> str | None:
        return self.instance.failure_reason if self.instance is not None else self._failure_reason


class ExtensionRegistry:
    """统一管理代码、无代码和未加载扩展记录的注册容器。"""

    def __init__(self) -> None:
        self.records: dict[str, ExtensionRecord] = {}

    @property
    def extensions(self) -> dict[str, Extension]:
        """返回已实例化的代码扩展。"""
        return {key: record.instance for key, record in self.records.items() if record.instance is not None}

    def clear(self) -> None:
        """清空全部注册项。"""
        self.records.clear()

    # ===== 扩展 =====

    def register_record(self, extension_id: str, record: ExtensionRecord) -> None:
        """登记代码、无代码或未加载扩展的统一记录。"""
        if extension_id in self.records:
            logger.warning(f'Extension {extension_id} registered twice, keeping the latest one.')
        self.records[extension_id] = record

    def unregister_extension(self, extension_id: str) -> None:
        """注销一个扩展实例，不存在时静默忽略。"""
        self.records.pop(extension_id, None)

    def unregister_by_owner(self, extension_id: str) -> list[str]:
        """注销扩展运行记录，返回被移除的扩展 id 列表。"""
        removed = [extension_id] if extension_id in self.records else []
        self.records.pop(extension_id, None)
        return removed
