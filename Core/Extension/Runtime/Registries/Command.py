"""
命令注册表：`command_id -> Command` 的纯容器。

只保存已登记的命令实例与归属扩展，不参与校验与 matcher 构建
（校验/构建由 `Managers/Command.py` 负责）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from Core.Logging import logger

from ...Errors import CommandError

if TYPE_CHECKING:
    from ...Command import Command


class CommandRegistry:
    """已登记命令的注册容器：command_id -> Command。"""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        # command_id -> 归属扩展 id（内置命令为 'builtin'）
        self._owners: dict[str, str] = {}

    def clear(self) -> None:
        """清空全部登记项。"""
        self._commands.clear()
        self._owners.clear()

    def register(self, command_id: str, command: Command, *, owner_id: str = '', override: bool = False) -> None:
        """
        登记一个命令实例。

        `override=True` 时允许以同名 `command_id` 取代已登记命令（用于扩展
        覆盖内置命令）；否则重复 `command_id` 视为冲突并报错。
        """
        if command_id in self._commands:
            if not override:
                raise CommandError(f'Command {command_id} registered twice, conflict rejected!')
            logger.info(f'Command {command_id} has been overridden.')
        self._commands[command_id] = command
        self._owners[command_id] = owner_id

    def unregister(self, command_id: str) -> None:
        """注销单个命令，不存在时静默忽略。"""
        self._commands.pop(command_id, None)
        self._owners.pop(command_id, None)

    def unregister_by_owner(self, owner_id: str) -> list[str]:
        """注销某个扩展登记的全部命令，返回被移除的 command_id 列表。"""
        removed = [command_id for command_id, owner in self._owners.items() if owner == owner_id]
        for command_id in removed:
            self.unregister(command_id)
        return removed

    def get(self, command_id: str) -> Command | None:
        """按 command_id 获取命令实例，未登记返回 None。"""
        return self._commands.get(command_id)

    def owner_of(self, command_id: str) -> str:
        """获取命令的归属扩展 id（未登记或内置命令返回空串/`builtin`）。"""
        return self._owners.get(command_id, '')

    def all(self) -> dict[str, Command]:
        """返回全部已登记命令的浅拷贝：command_id -> Command。"""
        return dict(self._commands)

    def __contains__(self, command_id: str) -> bool:
        return command_id in self._commands

    def __len__(self) -> int:
        return len(self._commands)
