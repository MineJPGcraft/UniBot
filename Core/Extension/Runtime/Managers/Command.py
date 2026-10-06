"""
命令管理器（运行时）：校验命令树并构建 Alconna matcher。

命令登记状态委托给 `Registries/Command.py` 容器，本管理器只负责
校验、构建、路由与清理。命令基类与参数模型见 `../../Command.py`，
扩展作者无需接触本模块。
"""

import inspect
from collections.abc import AsyncIterable
from functools import wraps
from typing import Any

from arclet.alconna import Alconna, Args, Subcommand
from nonebot.exception import FinishedException
from nonebot.matcher import MatcherSource
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_alconna.uniseg import Image, UniMessage

from Core.Config import config
from Core.Logging import exception_logger, logger
from Core.Rules import command_group_rule
from Core.Utils import turn_message_text

from ...Command import _NAME_PATTERN, UNSET, Command, Handler, SubCommand
from ...Errors import CommandError, CommandFieldError
from ..Registries import CommandRegistry


def _format_path(extension_id: str, path: list[str]) -> str:
    """格式化字段路径，如 `MyExt.command.weather.argument.city`。"""
    return f'{extension_id}.' + '.'.join(path)


def _validate_name(value: str, extension_id: str, path: list[str]) -> None:
    """校验命令/别名/参数名合法。"""
    if not _NAME_PATTERN.match(value):
        raise CommandFieldError(
            f'{_format_path(extension_id, path)} has invalid name: {value} (only lowercase letters, digits and underscores are allowed)'
        )


def _command_source(command: Command) -> MatcherSource | None:
    """构造指向命令类声明位置的 MatcherSource，供框架日志与帮助展示使用。"""
    command_cls = command.__class__
    module = inspect.getmodule(command_cls)
    if module is None:
        return None
    try:
        _, lineno = inspect.getsourcelines(command_cls)
    except OSError:
        return None
    return MatcherSource(module_name=module.__name__, lineno=lineno)


# ===== 命令管理器 =====


class CommandManager:
    """统一校验并构建所有命令 matcher，命令登记状态由 CommandRegistry 持有。"""

    # 稳定 command_id 中各段的连接符（如 `extension:MyExt:weather`）
    command_id_separator = ':'

    def __init__(self, registry: CommandRegistry | None = None) -> None:
        # 注册容器由 ExtensionManager 创建后按引用传入；独立使用（测试）时自建
        self._registry = registry if registry is not None else CommandRegistry()
        self._built = False
        self._matchers: list[Any] = []

    # ----- 注册阶段 -----

    def register_command(
        self, command: Command, command_id: str, *, override: bool = False, owner_id: str = ''
    ) -> None:
        """
        登记一个命令实例（内置或扩展）。

                `override=True` 时允许以同名 `command_id` **取代**已登记的命令（用于指令
                扩展覆盖内置命令）；否则重复 `command_id` 视为冲突并报错。
        """
        if self._built:
            raise CommandError('Command manager already built, no more commands can be registered!')
        self._registry.register(command_id, command, owner_id=owner_id, override=override)

    def unregister_by_owner(self, owner_id: str) -> list[str]:
        """注销某扩展登记的全部命令（声明回滚用；不处理已构建 matcher）。"""
        return self._registry.unregister_by_owner(owner_id)

    def get_command(self, command_id: str) -> Command | None:
        return self._registry.get(command_id)

    def get_command_nodes(self) -> dict[str, Command]:
        """返回全部已登记命令：稳定 command_id -> 命令实例。"""
        return self._registry.all()

    # ----- 校验阶段 -----

    def _validate_node(self, command: Command, extension_id: str, path: list[str]) -> None:
        """校验单个命令实例的字段合法性。"""
        _validate_name(command.name, extension_id, path + ['name'])

        seen_names: set[str] = set()
        for argument in command.arguments:
            argument_path = path + ['argument', argument.name]
            _validate_name(argument.name, extension_id, argument_path)
            if argument.name in seen_names:
                raise CommandFieldError(f'{_format_path(extension_id, argument_path)} argument name duplicated!')
            seen_names.add(argument.name)
            if not argument.required and argument.default is UNSET:
                raise CommandFieldError(
                    f'{_format_path(extension_id, argument_path)} optional argument must provide a default value!'
                )

        seen_subcommands: set[str] = set()
        for subcommand in command.subcommands:
            subcommand_path = path + ['subcommand', subcommand.name]
            _validate_name(subcommand.name, extension_id, subcommand_path)
            if subcommand.name in seen_subcommands:
                raise CommandFieldError(f'{_format_path(extension_id, subcommand_path)} subcommand name duplicated!')
            seen_subcommands.add(subcommand.name)
            self._validate_node(subcommand, extension_id, subcommand_path)

    def validate(self) -> None:
        """校验全部命令定义，失败时不注册任何 matcher。"""
        for command_id, command in self._registry.all().items():
            extension_id = self._command_extension(command_id)
            self._validate_node(command, extension_id, ['command', command.name])

    @staticmethod
    def _command_extension(command_id: str) -> str:
        """从 command_id 中提取扩展 id（如 `extension:MyExt:weather`）。"""
        parts = command_id.split(CommandManager.command_id_separator)
        if len(parts) >= 3 and parts[0] == 'extension':
            return parts[1]
        return 'builtin'

    # ----- 构建阶段 -----

    def _build_args(self, command: Command) -> Args:
        """将参数定义转换为 Alconna Args。"""
        args = Args()
        for argument in command.arguments:
            args += argument.to_alconna_args()
        return args

    def _build_subcommand(self, subcommand: SubCommand[Any]) -> Subcommand:
        """将子命令实例递归转换为 Alconna Subcommand（支持嵌套子命令）。"""
        nested = [self._build_subcommand(sub) for sub in subcommand.subcommands]
        return Subcommand(
            subcommand.name,
            self._build_args(subcommand),
            *nested,
            help_text=subcommand.description or None,
        )

    def _build_matcher(self, command: Command) -> None:
        """
        为一个命令实例构建 Alconna matcher 并绑定 handler。

                图像模式开启且命令声明了 image_handler 时，自动绑定图片处理器并直接
                发送渲染结果；否则回退到文本 handler。
        """
        subcommands = [self._build_subcommand(sub) for sub in command.subcommands]
        alconna = Alconna(
            command.name,
            self._build_args(command),
            *subcommands,
        )
        # 写入描述与用法，供 Help 等功能读取
        alconna.meta.description = command.description or 'Unknown'
        if command.usage:
            alconna.meta.usage = command.usage
        matcher = on_alconna(
            alconna,
            rule=command_group_rule,
            aliases=tuple(command.aliases) if command.aliases else None,
            block=True,
            priority=0,
            use_cmd_start=True,
            skip_for_unmatch=True,
        )
        # Alconna 把 matcher 位置记录为 on_alconna 调用处（本文件），重映射为命令类实际声明位置
        if source := _command_source(command):
            matcher._source = source
            alconna.meta.extra['matcher.source'] = source
        matcher.assign('$main')(self._route(matcher, command.image_handler, command.handler, command))
        # 递归注册子命令分派：叶子优先（后序遍历），父级子命令在嵌套子命令之后匹配，
        # 保证 `/bot superusers add 123` 命中 `add` 而非 `superusers`
        for subcommand in command.subcommands:
            self._assign_subcommand(matcher, subcommand, subcommand.name)
        self._matchers.append(matcher)
        logger.debug(f'Command {command.name} built.')

    def _assign_subcommand(self, matcher, subcommand: SubCommand[Any], path: str) -> None:
        """递归注册子命令分派处理器，路径用点路径（如 `superusers.add`）。"""
        for nested in subcommand.subcommands:
            self._assign_subcommand(matcher, nested, f'{path}.{nested.name}')
        matcher.assign(path)(self._route(matcher, subcommand.image_handler, subcommand.handler, subcommand))

    def _route(self, matcher, image_handler, handler: Handler, command: Command) -> Handler:
        """
        绑定处理器并统一处理返回值。

                图像模式生效且命令覆写了图片处理器时优先走图片处理器，否则走文本
                处理器。处理器通过 `return` 携带要发送的内容（字符串 / 图片字节 /
                片段列表 / 异步迭代器），框架在此统一发送，命令内无需接触 matcher。

                异步迭代器（async generator）返回值会被逐项收集，并用 turn_message_text
                转成多行文本发送；此时 `return` 仅做提前跳出函数用，不承载要发送的消息。
                dispatcher 通过 functools.wraps 继承 handler 的签名，使其业务参数
                （如 Uninfo、Match）照常由 nonebot 注入。
        """
        has_image_handler = type(command).image_handler is not Command.image_handler
        target = image_handler if config.image.mode and has_image_handler else handler

        @wraps(target)
        async def dispatched(*args, **kwargs):
            try:
                # 异步生成器：不 await，逐项收集后转多行文本发送
                if inspect.isasyncgenfunction(target):
                    await matcher.finish(await turn_message_text(target(*args, **kwargs)))
                    return None
                result = await target(*args, **kwargs)
                if result is None:
                    return None
                message = result
                if isinstance(result, AsyncIterable):
                    message = await turn_message_text(result)
                # 图片处理器返回 PNG 字节，包装为图片消息发送
                if isinstance(message, bytes):
                    message = UniMessage(Image(raw=message))
                return await matcher.finish(message)
            except FinishedException:
                pass
            except Exception as error:
                # 渲染/处理失败：记录日志并发送错误提示，不让异常中断机器人
                exception_logger.error(f'Command {command.name} handler failed: {error}')
                await matcher.finish(f'命令执行失败：{error}')

        return dispatched

    def cleanup_matchers(self) -> None:
        """注销全部已构建 matcher 并清空登记状态（热重载前调用）。"""
        for matcher in self._matchers:
            try:
                matcher.clean()
            except Exception as error:
                logger.error(f'Failed to unregister matcher {matcher}: {error}')
        self.clear()

    def clear(self) -> None:
        """清空全部已登记命令与构建状态（测试隔离与热重载使用）。"""
        self._registry.clear()
        self._matchers = []
        self._built = False

    def build(self) -> list:
        """校验全部命令并构建 matcher，任一失败则整体失败。"""
        if self._built:
            return self._matchers
        self.validate()
        for command in self._registry.all().values():
            self._build_matcher(command)
        self._built = True
        return self._matchers
