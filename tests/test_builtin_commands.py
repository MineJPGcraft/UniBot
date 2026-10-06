"""
内置指令重构测试：单文件扩展经 Loader 加载产生 builtin: 前缀（验证点 3、4、11）。

真实内置扩展（Extensions/*.py）依赖 config/Globals/Managers/Messages 等运行时模块，
测试不直接导入，改用轻量假命令类 + 假扩展实例，验证 Loader._commit_commands 的
内置命令前缀逻辑与 CommandManager 结构。
"""

from typing import override

import pytest

from Core.Extension import Command, CommandError, CommandManager, RendererManager, SubCommand
from Core.Extension.Runtime.Loader import ExtensionLoader
from Core.Extension.Runtime.Registries import ExtensionRegistries


def _make_extension(command_cls: type) -> 'object':
    """构造一个声明了单个命令类的假扩展实例。"""
    from Core.Extension import Extension

    extension = Extension()
    extension.commands = [command_cls]
    return extension


def _commit(commands: dict[str, 'object'], builtin: bool = True):
    """
    用假扩展实例驱动 Loader._commit_commands，模拟扩展声明阶段。

        Loader 把命令登记到底层 CommandRegistry；命令管理器经 `loader._command_manager`
        取回（每个 Loader 独立，测试天然隔离）。
    """
    loader = ExtensionLoader(ExtensionRegistries(), RendererManager())
    for extension_id, extension in commands.items():
        loader._commit_commands(extension_id, extension, builtin=builtin)
    return loader._command_manager


def _build_all(manager: CommandManager):
    manager.validate()
    manager.build()


# ===== 假命令类 =====


class _AboutCommand(Command):
    name = 'about'
    description = '关于'

    class Check(SubCommand):
        name = 'check'
        description = '检查更新'


class _BoundCommand(Command):
    name = 'bound'
    description = '绑定'

    class List(SubCommand):
        name = 'list'
        description = '列出'

    class Query(SubCommand):
        name = 'query'
        description = '查询'

    class Remove(SubCommand):
        name = 'remove'
        description = '移除'

    class Append(SubCommand):
        name = 'append'
        description = '添加'


class _ConsoleCommand(Command):
    name = 'command'
    description = '执行命令'

    @override
    def declare(self) -> None:
        self.register_arg('server', str, description='服务器')
        self.register_arg('command', str, description='命令', multi=True)


class _HelpCommand(Command):
    name = 'help'
    description = '帮助'
    usage = '/help [命令名称]'

    @override
    def declare(self) -> None:
        self.register_option('command', str, default=None, description='命令名称')


class _SendCommand(Command):
    name = 'send'
    description = '发送'
    aliases = ('mc',)

    @override
    def declare(self) -> None:
        self.register_arg('message', str, description='消息', multi=True)


class _ListCommand(Command):
    name = 'list'
    description = '列表'


class _LuckCommand(Command):
    name = 'luck'
    description = '人品'


class _ServerCommand(Command):
    name = 'server'
    description = '服务器'


class _NestedCommand(Command):
    """带两级嵌套子命令的命令（如 /bot superusers add）。"""

    name = 'bot'
    description = '机器人'

    class Superusers(SubCommand):
        name = 'superusers'
        description = '管理超级用户'

        class Add(SubCommand):
            name = 'add'
            description = '添加'

            @override
            def declare(self) -> None:
                self.register_arg('target', str, description='目标')

        class Remove(SubCommand):
            name = 'remove'
            description = '移除'

            @override
            def declare(self) -> None:
                self.register_arg('target', str, description='目标')


# ===== 收集 =====


class TestBuiltinCollection:
    def test_all_enabled_commands_registered(self):
        manager = _commit(
            {
                'About': _make_extension(_AboutCommand),
                'Bound': _make_extension(_BoundCommand),
                'Command': _make_extension(_ConsoleCommand),
                'Help': _make_extension(_HelpCommand),
                'List': _make_extension(_ListCommand),
                'Luck': _make_extension(_LuckCommand),
                'Send': _make_extension(_SendCommand),
                'Server': _make_extension(_ServerCommand),
            }
        )
        nodes = manager.get_command_nodes()
        names = {node.name for node in nodes.values()}
        assert names == {'about', 'bound', 'command', 'help', 'list', 'luck', 'send', 'server'}

    def test_command_ids_use_builtin_prefix(self):
        manager = _commit({'Send': _make_extension(_SendCommand)})
        nodes = manager.get_command_nodes()
        assert all(cid.startswith('builtin:') for cid in nodes)

    def test_extension_prefix_used_for_non_builtin(self):
        """非内置扩展命令使用 extension: 前缀。"""

        extension = _make_extension(_SendCommand)
        manager = _commit({'WeatherExt': extension}, builtin=False)
        assert 'extension:WeatherExt:send' in manager.get_command_nodes()

    def test_register_after_build_raises(self):
        manager = _commit({'Send': _make_extension(_SendCommand)})
        _build_all(manager)
        with pytest.raises(CommandError):
            manager.register_command(_SendCommand(), 'builtin:send')


# ===== 结构 =====


class TestBuiltinStructure:
    def test_command_has_multi_argument(self):
        manager = _commit({'Command': _make_extension(_ConsoleCommand)})
        node = manager.get_command('builtin:command')
        message_arg = node.find_argument('command')
        assert message_arg is not None
        assert message_arg.multi is True

    def test_send_has_alias(self):
        manager = _commit({'Send': _make_extension(_SendCommand)})
        node = manager.get_command('builtin:send')
        assert 'mc' in node.aliases

    def test_bound_has_four_subcommands(self):
        manager = _commit({'Bound': _make_extension(_BoundCommand)})
        node = manager.get_command('builtin:bound')
        names = {sub.name for sub in node.subcommands}
        assert names == {'list', 'query', 'remove', 'append'}

    def test_about_has_check_subcommand(self):
        manager = _commit({'About': _make_extension(_AboutCommand)})
        node = manager.get_command('builtin:about')
        assert node.find_subcommand('check') is not None

    def test_help_has_optional_argument(self):
        manager = _commit({'Help': _make_extension(_HelpCommand)})
        node = manager.get_command('builtin:help')
        command_arg = node.find_argument('command')
        assert command_arg is not None
        assert command_arg.required is False

    def test_help_has_usage_and_description(self):
        manager = _commit({'Help': _make_extension(_HelpCommand)})
        node = manager.get_command('builtin:help')
        assert node.usage
        assert node.description

    def test_build_creates_matchers(self):
        manager = _commit(
            {
                'About': _make_extension(_AboutCommand),
                'Bound': _make_extension(_BoundCommand),
                'Command': _make_extension(_ConsoleCommand),
                'Help': _make_extension(_HelpCommand),
                'List': _make_extension(_ListCommand),
                'Luck': _make_extension(_LuckCommand),
                'Send': _make_extension(_SendCommand),
                'Server': _make_extension(_ServerCommand),
            }
        )
        _build_all(manager)
        assert len(manager._matchers) == 8


# ===== 嵌套子命令 =====


class TestNestedSubcommand:
    def test_nested_subcommand_discovered(self):
        """两级嵌套子命令被自动发现，parent 链正确。"""
        manager = _commit({'Bot': _make_extension(_NestedCommand)})
        node = manager.get_command('builtin:bot')
        superusers = node.find_subcommand('superusers')
        assert superusers is not None
        add = superusers.find_subcommand('add')
        assert add is not None
        assert add.find_argument('target') is not None
        # parent 链：add -> superusers -> bot
        assert add.parent is superusers
        assert superusers.parent is node

    def test_nested_subcommand_builds_nested_alconna(self):
        """构建出的 Alconna 中嵌套子命令是父子结构而非拍平。"""
        manager = _commit({'Bot': _make_extension(_NestedCommand)})
        _build_all(manager)
        alconna = manager._matchers[0].command()
        help_text = alconna.get_help()
        # 嵌套子命令以「父级下的子命令」形式出现（非独立顶层子命令）
        assert 'superusers' in help_text
        assert 'add' in help_text
        # 顶层子命令列表应只包含 superusers，add 是它的下级
        top_level = [sub.name for sub in alconna.options if getattr(sub, 'dest', None) == 'superusers']
        assert top_level == ['superusers']

    def test_nested_subcommand_parse(self):
        """`/bot superusers add 123` 正确解析，add 不作为一级子命令暴露。"""
        manager = _commit({'Bot': _make_extension(_NestedCommand)})
        _build_all(manager)
        alconna = manager._matchers[0].command()
        from arclet.alconna import command_manager as alconna_command_manager

        with alconna_command_manager.update(alconna):
            alconna.prefixes = ['/']
        result = alconna.parse('/bot superusers add 123')
        assert result.matched
        assert list(result.subcommands) == ['superusers']
        assert result.query('superusers.add.target') == '123'
        # 修复前 bug：add 被拍平为一级子命令，/bot add 123 也能触发
        assert not alconna.parse('/bot add 123').matched


# ===== 单文件清单构建 =====


class TestManifestFromAttributes:
    def test_builds_manifest_from_class_attributes(self):
        from Core.Extension import Extension, ExtensionType, manifest_from_attributes

        class FakeExt(Extension):
            id = 'Fake'
            name = '假扩展'
            version = '1.0.0'
            types = ('command',)

        manifest = manifest_from_attributes(FakeExt())
        assert manifest.extension.id == 'Fake'
        assert manifest.extension.name == '假扩展'
        assert manifest.extension.types == [ExtensionType('command')]

    def test_builds_manifest_from_constructor_kwargs(self):
        """直接实例化 Extension 并传入元数据参数，无需继承。"""
        from Core.Extension import Extension, ExtensionType, manifest_from_attributes

        extension = Extension(id='Fake', name='假扩展', version='1.0.0', types=('command',))
        manifest = manifest_from_attributes(extension)
        assert manifest.extension.id == 'Fake'
        assert manifest.extension.name == '假扩展'
        assert manifest.extension.types == [ExtensionType('command')]

    def test_missing_id_raises(self):
        from Core.Extension import Extension, ManifestError, manifest_from_attributes

        class FakeExt(Extension):
            name = '假扩展'
            version = '1.0.0'

        with pytest.raises(ManifestError):
            manifest_from_attributes(FakeExt())

    def test_constructor_without_id_raises(self):
        from Core.Extension import Extension, ManifestError, manifest_from_attributes

        extension = Extension(name='假扩展', version='1.0.0')
        with pytest.raises(ManifestError):
            manifest_from_attributes(extension)
