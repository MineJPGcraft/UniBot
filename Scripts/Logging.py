"""日志统一配置：彩色控制台输出、文件归档与模块名美化。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger as default_logger
from nonebot import get_driver
from nonebot.log import default_filter

# 统一导出的 logger：默认开启消息颜色标签解析（等价于每次调用 opt(colors=True)），
# 控制台渲染 ANSI 彩色，文件日志（colorize=False）自动剥离标签保持纯净文本。
logger = default_logger.opt(colors=True)

# 需要打印完整异常堆栈的日志直接使用此 logger（等价于 logger.opt(exception=True)）。
exception_logger = logger.opt(exception=True)

if TYPE_CHECKING:
    from loguru import HandlerConfig, Record

# 模块名前缀 → 展示名，按前缀长度从长到短排列
MODULE_ALIASES: tuple[tuple[str, str], ...] = (
    ('Scripts.Connectors', 'Conn'),
    ('Scripts.Extensions.Builtin', 'Builtin'),
    ('Scripts.Extensions', 'Ext'),
    ('Scripts.Managers', 'Mgr'),
    ('Scripts.Api', 'WebApi'),
    ('Scripts.Plugins', 'Plg'),
    ('Scripts', 'Core'),
    ('nonebot_plugin_alconna', 'Alconna'),
    ('nonebot', 'NoneBot'),
    ('fastapi', 'FastAPI'),
)

# 模块名为空时的兜底展示名
FALLBACK_NAME = 'Unknown'


def resolve_module_alias(module_name: str | None) -> str:
    """将完整模块名映射为简短的展示名，提升日志辨识度。

    仅 Scripts 内部模块保留子模块名（如 Core.Config、Builtin.List），
    第三方模块只显示一级别名（如 uvicorn.lifespan.on → HTTP）。
    """
    if not module_name:
        return FALLBACK_NAME
    # 入口文件（Bot.py / Watchdog.py）统一显示为 Bot
    if module_name == '__main__':
        return 'Bot'
    for prefix, alias in MODULE_ALIASES:
        if module_name == prefix:
            return alias
        if module_name.startswith(f'{prefix}.'):
            if prefix.startswith('Scripts'):
                remainder = module_name[len(prefix) + 1 :]
                # 内置扩展去掉 Commands./Services. 中间层，避免展示名过长
                if prefix == 'Scripts.Extensions.Builtin':
                    remainder = remainder.removeprefix('Commands.')
                    remainder = remainder.removeprefix('Services.')
                return f'{alias}/{remainder}'
            return alias
    # 未匹配的第三方模块只显示第一级模块名
    return module_name.split('.', 1)[0].capitalize()


def _patch_record(record: Record) -> None:
    """将完整模块名美化为短展示名，供格式渲染。"""
    record['name'] = resolve_module_alias(record['name'])


def console_format(record: Record) -> str:
    """控制台日志格式：时间、级别、模块名渲染（接近 NoneBot 默认风格）。"""
    # NoneBot init() 期间内置 patcher 会把模块名截断为小写 nonebot，这里兜底统一
    name = 'NoneBot' if record['name'] == 'nonebot' else record['name']
    # 函数格式不会像字符串格式那样自动追加异常占位符，必须显式包含 {exception}，
    # 否则带堆栈的日志（如 uvicorn 的 Exception in ASGI application）只输出消息行
    return (
        f'<dim>{{time:MM-DD HH:mm:ss}}</dim> [<lvl>{{level}}</lvl>] '
        f'<light-cyan><u>{name}</u></light-cyan> | {{message}}\n{{exception}}'
    )


def file_format(record: Record) -> str:
    """文件日志格式：无色彩，保留模块定位信息。"""
    name = 'NoneBot' if record['name'] == 'nonebot' else record['name']
    return f'{{time:MM-DD HH:mm:ss}} [{{level}}] {name} | {{message}}\n{{exception}}'


def setup_level_colors() -> None:
    """为日志级别分配与 NoneBot 默认接近的颜色。"""
    logger.level('TRACE', color='<dim>')
    logger.level('DEBUG', color='<cyan>')
    logger.level('INFO', color='<white>')
    logger.level('ERROR', color='<light-red>')


def configure_handlers(log_path: Path | None = None) -> None:
    """在 NoneBot 初始化前配置日志处理器，保证启动早期日志格式统一。"""
    setup_level_colors()
    # logger.configure 传 handlers 会先移除全部旧处理器；
    # NoneBot 初始化时会重置 patcher 与 extra，故此处先兜底设置，init 后由 configure_logging 恢复
    handlers: list[HandlerConfig] = [
        {
            'sink': sys.stdout,
            'level': 0,
            'diagnose': False,
            'filter': default_filter,
            'format': console_format,
            'colorize': True,
        }
    ]
    if log_path is not None:
        handlers.append(
            {
                'sink': log_path / '{time}.log',
                'level': 0,
                'rotation': '1 day',
                'encoding': 'Utf-8',
                'diagnose': False,
                'format': file_format,
                'colorize': False,
            }
        )
    logger.configure(
        handlers=handlers,
        patcher=_patch_record,
        extra={'nonebot_log_level': 'INFO'},
    )


def configure_logging() -> None:
    """NoneBot 初始化后恢复自定义 patcher，并同步真实日志级别。"""
    logger.configure(
        patcher=_patch_record,
        extra={'nonebot_log_level': get_driver().config.log_level},
    )
