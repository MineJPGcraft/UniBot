"""测试全局配置：初始化 NoneBot 并准备扩展系统测试环境。"""

import sys
from pathlib import Path

import pytest

# 确保 UniBot 根目录在 sys.path 中，使 `from Scripts...` 可导入
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import nonebot  # noqa: E402

# 必须在任何 Scripts 模块导入前初始化（Config.py 顶层调用 get_plugin_config）
nonebot.init()


@pytest.fixture(scope='session', autouse=True)
def _init_nonebot():
    """所有测试开始前初始化 NoneBot。"""
    nonebot.init()


@pytest.fixture(autouse=True)
def _isolate_extension_manager():
    """每个测试前清空扩展管理器状态，避免测试间相互污染。"""
    from Scripts.Extensions import command_manager, extension_manager

    extension_manager.reset()
    command_manager._commands.clear()
    command_manager._built = False
    command_manager._matchers = []
    yield
    extension_manager.reset()
    command_manager._commands.clear()
    command_manager._built = False
    command_manager._matchers = []
