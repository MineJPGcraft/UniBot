"""指令注册测试：命令类发现、嵌套子命令与字段校验（验证点 3、4、11）。"""

import inspect
from typing import override

import pytest

from Scripts.Extensions import (
    Command,
    CommandError,
    CommandFieldError,
    CommandManager,
    SubCommand,
)


def discover_commands(module) -> list[Command]:
    """扫描模块中非抽象、非 SubCommand 的 Command 子类并实例化（测试辅助）。"""
    commands = []
    for _, member in inspect.getmembers(module, inspect.isclass):
        if member is Command or member is SubCommand or not issubclass(member, Command):
            continue
        if issubclass(member, SubCommand) or inspect.isabstract(member):
            continue
        commands.append(member())
    return commands


class WeatherCommand(Command):
    """天气命令。"""

    name = 'weather'
    description = '天气'

    @override
    def declare(self) -> None:
        self.register_arg('city', str, description='城市')

    class Today(SubCommand['WeatherCommand']):
        name = 'today'
        description = '今天'

        @override
        def declare(self) -> None:
            self.register_arg('city', str, required=False, default='SH')


async def handler(*args, **kwargs):
    pass


# ===== 命令类发现与收集 =====


class TestCommandDiscovery:
    def test_discover_commands_instantiates_command_class(self):
        module = type('FakeModule', (), {'WeatherCommand': WeatherCommand})
        commands = discover_commands(module)
        names = [command.name for command in commands]
        assert names == ['weather']

    def test_discover_skips_subcommand_only_class(self):
        class OnlySub(SubCommand):
            name = 'onlysub'

        module = type('FakeModule', (), {'OnlySub': OnlySub})
        assert discover_commands(module) == []

    def test_nested_subcommand_collected_with_parent(self):
        command = WeatherCommand()
        assert len(command.subcommands) == 1
        today = command.find_subcommand('today')
        assert today is not None
        assert today.parent is command

    def test_subcommand_arguments_isolated_from_parent(self):
        command = WeatherCommand()
        today = command.find_subcommand('today')
        assert len(command.arguments) == 1
        assert len(today.arguments) == 1
        assert command.find_argument('city') is not None
        assert today.find_argument('city') is not None


# ===== 注册接口 =====


class TestRegistration:
    def test_register_arg(self):
        command = WeatherCommand()
        argument = command.register_arg('region', str, description='地区')
        assert argument in command.arguments
        assert argument.required is True

    def test_register_option_defaults_not_required(self):
        command = WeatherCommand()
        option = command.register_option('unit', str, default='c', description='单位')
        assert option in command.arguments
        assert option.required is False
        assert option.default == 'c'

    def test_register_subcommand(self):
        command = WeatherCommand()
        sub = SubCommand(command)
        sub.name = 'tomorrow'
        returned = command.register_subcommand(sub)
        assert returned is sub
        assert command.find_subcommand('tomorrow') is sub


# ===== CommandManager 校验 =====


class TestCommandValidation:
    def _manager(self, command: Command) -> CommandManager:
        manager = CommandManager()
        manager.register_command(command, 'builtin:weather')
        return manager

    def test_valid_command_passes(self):
        manager = self._manager(WeatherCommand())
        manager.validate()

    def test_duplicate_argument_name_detected(self):
        class DupArg(Command):
            name = 'dup'

            @override
            def declare(self) -> None:
                self.register_arg('city', str)
                self.register_arg('city', str)

        manager = self._manager(DupArg())
        with pytest.raises(CommandFieldError):
            manager.validate()

    def test_optional_argument_needs_default(self):
        class NoDefault(Command):
            name = 'nodefault'

            @override
            def declare(self) -> None:
                self.register_arg('city', str, required=False)

        manager = self._manager(NoDefault())
        with pytest.raises(CommandFieldError):
            manager.validate()

    def test_duplicate_subcommand_detected(self):
        class DupSub(Command):
            name = 'dupsub'

            class Today(SubCommand):
                name = 'today'

            class AlsoToday(SubCommand):
                name = 'today'

        manager = self._manager(DupSub())
        with pytest.raises(CommandFieldError):
            manager.validate()

    def test_register_after_build_raises(self):
        manager = CommandManager()
        manager.register_command(WeatherCommand(), 'builtin:weather')
        manager.build()
        with pytest.raises(CommandError):
            manager.register_command(WeatherCommand(), 'builtin:other')

    def test_duplicate_command_id_raises(self):
        manager = CommandManager()
        manager.register_command(WeatherCommand(), 'builtin:weather')
        with pytest.raises(CommandError):
            manager.register_command(WeatherCommand(), 'builtin:weather')

    def test_optional_args_do_not_inject_default(self):
        """default 为 None 的可选参数不应向 Alconna 注入默认值，否则 available 恒 True。"""

        class OptionalCmd(Command):
            name = 'opt'

            @override
            def declare(self) -> None:
                self.register_option('server', str, default=None, description='服务器')

        manager = CommandManager()
        manager.register_command(OptionalCmd(), 'builtin:opt')
        args = manager._build_args(OptionalCmd())
        arg_list = list(args)
        assert len(arg_list) == 1
        assert arg_list[0].name == 'server'
        assert arg_list[0].optional is True
        # 未注入默认值：field.default 保持 inspect._empty
        from inspect import _empty

        assert arg_list[0].field.default is _empty

    def test_optional_args_inject_non_none_default(self):
        """声明了非 None default 的可选参数，直接注入 Alconna，由 Alconna 填充。"""

        class DefaultCmd(Command):
            name = 'defcmd'

            @override
            def declare(self) -> None:
                self.register_option('city', str, default='Shanghai', description='城市')

        manager = CommandManager()
        manager.register_command(DefaultCmd(), 'builtin:defcmd')
        args = manager._build_args(DefaultCmd())
        arg_list = list(args)
        assert len(arg_list) == 1
        assert arg_list[0].name == 'city'
        assert arg_list[0].optional is True
        assert arg_list[0].field.default == 'Shanghai'
