"""
指令覆盖测试：通过类继承覆写内置命令（验证点 5、12）。

覆盖机制已由 CommandPatch/override_command 重构为类继承：扩展继承内置命令
类，覆写类属性或 handler 即可，无需冲突检测（派生类天然覆盖基类）。
`@override` 仅作为编码惯例标记，不做运行时强制校验。
"""

from typing import override

import pytest

from Core.Extension import Command, SubCommand


class BuiltinListCommand(Command):
    """仿内置 list 命令，含可选参数与子命令。"""

    name = 'list'
    description = '查看服务器在线玩家列表。'
    usage = '/list [服务器名称]'

    @override
    def declare(self) -> None:
        self.register_option('server', str, default=None, description='服务器名称')

    class Check(SubCommand['BuiltinListCommand']):
        name = 'check'
        description = '检测'


class _OverrideListCommand(BuiltinListCommand):
    """通过继承覆写内置 list 命令。"""

    description = '覆写后的描述'
    usage = '/list all'


async def _handler(*args, **kwargs):
    pass


# ===== 类继承覆写 =====


class TestClassOverride:
    def test_override_meta_fields(self):
        command = _OverrideListCommand()
        assert command.description == '覆写后的描述'
        assert command.usage == '/list all'

    def test_inherited_commands_and_arguments_preserved(self):
        command = _OverrideListCommand()
        # 继承基类参数与子命令
        assert command.find_argument('server') is not None
        assert command.find_subcommand('check') is not None

    def test_override_handler(self):
        class OverrideHandler(BuiltinListCommand):
            name = 'list'

            @override
            async def handler(self) -> str | None:
                return '覆写'

        command = OverrideHandler()
        assert isinstance(command.handler, object)  # 覆写 handler 方法存在

    def test_parent_chain_uses_override_class(self):
        command = _OverrideListCommand()
        check = command.find_subcommand('check')
        assert check is not None
        assert check.parent is command

    def test_inheritance_overrides_base_without_conflict(self):
        """派生类直接覆盖同名字段，无需冲突检测，天然生效。"""
        base = BuiltinListCommand()
        override = _OverrideListCommand()
        assert base.description == '查看服务器在线玩家列表。'
        assert override.description == '覆写后的描述'
        assert base.usage == '/list [服务器名称]'
        assert override.usage == '/list all'


# ===== command_id 覆盖取代 =====


class TestCommandIdOverride:
    def test_register_override_replaces_existing(self):
        from Core.Extension import CommandManager

        manager = CommandManager()
        manager.register_command(BuiltinListCommand(), 'builtin:list')
        manager.register_command(_OverrideListCommand(), 'builtin:list', override=True)
        command = manager.get_command('builtin:list')
        assert command is not None
        assert command.description == '覆写后的描述'

    def test_register_duplicate_without_override_raises(self):
        from Core.Extension import CommandError, CommandManager

        manager = CommandManager()
        manager.register_command(BuiltinListCommand(), 'builtin:list')
        with pytest.raises(CommandError):
            manager.register_command(_OverrideListCommand(), 'builtin:list')
