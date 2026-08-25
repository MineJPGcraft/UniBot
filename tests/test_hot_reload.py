"""热重载测试：matcher 注销、模块缓存清理、语法预检与完整 reload 循环。"""

import asyncio
import sys
import types

import pytest

from Scripts.Extensions import Command, command_manager, extension_manager
from Scripts.Extensions.Loader import ExtensionLoader

# 单个内置命令的 NoneBot 优先级（Command.py 固定 priority=0）
_MATCHER_PRIORITY = 0


class _ReloadCommand(Command):
    name = 'greet'
    description = 'v1'

    async def handler(self) -> str:
        return 'hello v1'


# ===== CommandManager.cleanup_matchers =====


class TestCleanupMatchers:
    def test_cleanup_removes_matchers_and_resets_state(self):
        from arclet.alconna import command_manager as alconna_manager
        from nonebot.internal.matcher import matchers as nonebot_matchers

        command_manager.register_command(_ReloadCommand(), 'extension:Reload:greet')
        command_manager.build()
        matcher = command_manager._matchers[0]
        assert matcher in nonebot_matchers[_MATCHER_PRIORITY]
        assert command_manager._built is True
        assert command_manager._commands

        command_manager.cleanup_matchers()

        assert matcher not in nonebot_matchers[_MATCHER_PRIORITY]
        assert command_manager._built is False
        assert command_manager._matchers == []
        assert command_manager._commands == {}
        # arclet 的命令登记一并清除：get_command 未找到时抛 ValueError
        with pytest.raises(ValueError):
            alconna_manager.get_command('greet')

    def test_cleanup_twice_is_noop(self):
        command_manager.register_command(_ReloadCommand(), 'extension:Reload:greet')
        command_manager.build()
        command_manager.cleanup_matchers()
        # 第二次清理：_matchers 已空，不抛错
        command_manager.cleanup_matchers()
        assert command_manager._built is False


# ===== Loader.purge_modules / check_syntax =====


@pytest.fixture(autouse=True)
def _protect_builtin_modules():
    """快照并恢复内置扩展模块身份，防止热重载后其他测试的模块引用不匹配。"""
    snapshot = {
        name: sys.modules[name]
        for name in sys.modules
        if name.startswith('Scripts.Extensions.Builtin')
    }
    yield
    for name, module in snapshot.items():
        sys.modules[name] = module


class TestPurgeModules:
    def test_purge_removes_only_extension_modules(self):
        # 直接注册假扩展模块，模拟已导入的用户扩展（无需真实文件）
        fake_package = types.ModuleType('Extensions')
        fake_module = types.ModuleType('Extensions.Greet')
        sys.modules['Extensions'] = fake_package
        sys.modules['Extensions.Greet'] = fake_module

        loader = ExtensionLoader(extension_manager)
        try:
            loader.purge_modules()
        finally:
            sys.modules.pop('Extensions', None)
            sys.modules.pop('Extensions.Greet', None)

        assert 'Extensions.Greet' not in sys.modules
        # 框架模块不受影响
        assert 'Scripts.Extensions' in sys.modules
        assert 'Scripts.Extensions.Loader' in sys.modules


class TestCheckSyntax:
    def test_check_syntax_detects_bad_extension(self, tmp_path, monkeypatch):
        bad_dir = tmp_path / 'Extensions'
        bad_dir.mkdir()
        (bad_dir / 'Broken.py').write_text('def broken(:\n', encoding='Utf-8')
        (bad_dir / 'Good.py').write_text('x = 1\n', encoding='Utf-8')
        monkeypatch.setattr('Scripts.Extensions.Loader.EXTENSIONS_DIR', bad_dir)

        loader = ExtensionLoader(extension_manager)
        broken = loader.check_syntax()

        assert len(broken) == 1
        assert 'Broken.py' in broken[0]


# ===== 完整 reload 循环（真实单文件扩展） =====

_GREET_V1 = '''\
"""v1"""
from Scripts.Extensions import Command, Extension

extension = Extension(id="Greet", name="Greet", version="1.0.0", types=("command",))


@extension.register_command
class GreetCommand(Command):
    name = "greet"
    description = "v1 description"

    async def handler(self) -> str:
        return "hello v1"
'''

_GREET_V2 = '''\
"""v2"""
from Scripts.Extensions import Command, Extension

extension = Extension(id="Greet", name="Greet", version="2.0.0", types=("command",))


@extension.register_command
class GreetCommand(Command):
    name = "greet"
    description = "v2 description"

    async def handler(self) -> str:
        return "hello v2"
'''


@pytest.fixture
def greet_extension_dir(tmp_path, monkeypatch):
    """构造隔离的临时扩展环境（内置目录重定向为空目录，避免热重载真实内置扩展）。"""
    extension_dir = tmp_path / 'Extensions'
    extension_dir.mkdir()
    builtin_dir = tmp_path / 'Builtin'
    (builtin_dir / 'Commands').mkdir(parents=True)
    (builtin_dir / 'Services').mkdir()
    config_root = tmp_path / 'Config'
    config_root.mkdir()
    data_root = tmp_path / 'Data'
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setattr('Scripts.Extensions.Loader.EXTENSIONS_DIR', extension_dir)
    monkeypatch.setattr('Scripts.Extensions.Loader.BUILTIN_DIR', builtin_dir)
    monkeypatch.setattr('Scripts.Extensions.Loader.CONFIG_ROOT', config_root)
    monkeypatch.setattr('Scripts.Extensions.Loader.DATA_ROOT', data_root)
    yield extension_dir
    # 清理用户扩展模块与已构建 matcher（内置模块由 _protect_builtin_modules 恢复）
    for name in list(sys.modules):
        if name.startswith('Extensions.'):
            sys.modules.pop(name, None)
    command_manager.cleanup_matchers()
    sys.path.remove(str(tmp_path))


class TestReloadCycle:
    def test_reload_picks_up_code_changes(self, greet_extension_dir):
        from nonebot.internal.matcher import matchers as nonebot_matchers

        (greet_extension_dir / 'Greet.py').write_text(_GREET_V1, encoding='Utf-8')

        extension_manager.load()
        command_manager.build()
        assert extension_manager.registry['Greet'].metadata.version == '1.0.0'
        assert command_manager.get_command('extension:Greet:greet').description == 'v1 description'
        old_matcher = command_manager._matchers[0]
        registry_count = len(nonebot_matchers[_MATCHER_PRIORITY])

        # 修改扩展代码并热重载
        (greet_extension_dir / 'Greet.py').write_text(_GREET_V2, encoding='Utf-8')
        asyncio.run(extension_manager.reload())

        # 新代码生效：版本、命令描述、处理器输出均更新
        assert extension_manager.registry['Greet'].metadata.version == '2.0.0'
        command = command_manager.get_command('extension:Greet:greet')
        assert command.description == 'v2 description'
        assert asyncio.run(command.handler()) == 'hello v2'
        # matcher 已替换为新的类对象，且注册表数量无净增长（无泄漏）
        new_matcher = command_manager._matchers[0]
        assert new_matcher is not old_matcher
        assert old_matcher not in nonebot_matchers[_MATCHER_PRIORITY]
        assert new_matcher in nonebot_matchers[_MATCHER_PRIORITY]
        assert len(nonebot_matchers[_MATCHER_PRIORITY]) == registry_count

    def test_reload_aborts_on_syntax_error_keeping_old_state(self, greet_extension_dir):
        from nonebot.internal.matcher import matchers as nonebot_matchers

        (greet_extension_dir / 'Greet.py').write_text(_GREET_V1, encoding='Utf-8')
        extension_manager.load()
        command_manager.build()
        old_extension = extension_manager.registry['Greet']
        old_matcher = command_manager._matchers[0]

        # 写入语法错误的代码
        (greet_extension_dir / 'Greet.py').write_text('def broken(:\n', encoding='Utf-8')
        with pytest.raises(RuntimeError, match='syntax check failed'):
            asyncio.run(extension_manager.reload())

        # 旧状态完整保留：扩展实例、命令、matcher 均未受影响
        assert extension_manager.registry['Greet'] is old_extension
        assert command_manager.get_command('extension:Greet:greet').description == 'v1 description'
        assert old_matcher in nonebot_matchers[_MATCHER_PRIORITY]
        assert command_manager._built is True
