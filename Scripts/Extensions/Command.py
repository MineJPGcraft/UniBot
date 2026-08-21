"""
结构化命令注册与构建。

命令以类声明：继承 Command 定义主命令，类属性声明元数据，覆写 declare()
注册参数与子命令，覆写 handler()/image_handler() 提供业务逻辑。子命令通过
嵌套 SubCommand 类的形式声明，框架自动发现并实例化，parent 指向父命令实例。
"""

import inspect
import re
from abc import ABC
from collections.abc import AsyncIterable, Awaitable, Callable
from functools import wraps
from typing import Any, Generic, TypeVar

from arclet.alconna import Alconna, Args, MultiVar, Subcommand
from nonebot.exception import FinishedException
from nonebot.matcher import MatcherSource
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_alconna.uniseg import Image, UniMessage

from Scripts.Config import config
from Scripts.Logging import exception_logger, logger
from Scripts.Rules import command_group_rule
from Scripts.Utils import turn_message_text

from .Errors import CommandError, CommandFieldError

# 到内置命令的稳定前缀
BUILTIN_PREFIX = 'builtin'

# 未设置标记
UNSET = object()

# 命令名 / 别名 / 参数名的合法字符（小写字母、数字、下划线）
_NAME_PATTERN = re.compile(r'^[a-z0-9_]+$')

# 命令处理器：任意参数的异步可调用对象
Handler = Callable[..., Awaitable[Any]]

# 图片处理器：返回 PNG 图片字节的异步可调用对象
ImageHandler = Callable[..., Awaitable[bytes]]

# 父命令类型参数：子命令用它标注宿主命令类型，从而获得父命令方法提示
ParentT = TypeVar('ParentT', bound='Command')


def _format_path(extension_id: str, path: list[str]) -> str:
    """格式化字段路径，如 `MyExt.command.weather.argument.city`。"""
    return f'{extension_id}.' + '.'.join(path)


def _validate_name(value: str, extension_id: str, path: list[str]) -> None:
    """校验命令/别名/参数名合法。"""
    if not _NAME_PATTERN.match(value):
        raise CommandFieldError(f'{_format_path(extension_id, path)} has invalid name: {value} (only lowercase letters, digits and underscores are allowed)')


# ===== 参数构建器 =====


class Argument:
    """单个参数的结构化定义。"""

    def __init__(
        self,
        name: str,
        value_type: Any = str,
        required: bool = True,
        default: Any = UNSET,
        description: str = '',
        multi: bool = False,
    ) -> None:
        self.name = name
        self.value_type = value_type
        self.required = required
        self.default = default
        self.description = description
        # 是否接受多个值（对应 Alconna MultiVar，如 `str+`）
        self.multi = multi

    def _resolved_type(self) -> Any:
        """返回用于 Alconna Args 的实际类型（multi 时包装为 MultiVar）。"""
        if self.multi:
            return MultiVar(self.value_type, '+')
        return self.value_type


# ===== 命令基类 =====


class Command(Generic[ParentT], ABC):
    """
    命令基类：子类继承并声明元数据，覆写 declare() 注册参数与子命令，
        覆写 handler()/image_handler() 提供业务逻辑。子命令通过嵌套 SubCommand
        类的形式声明，框架自动发现并实例化。

        父命令 `parent` 通过泛型标注：`class Check(SubCommand['AboutCommand'])`
        使 `self.parent` 提示为 `AboutCommand`（非 None），从而自动补全父命令方法。
    """

    name: str = ''
    description: str = ''
    usage: str | None = None
    aliases: tuple[str, ...] = ()

    def __init__(self, parent: ParentT | None = None) -> None:
        # 父命令实例，运行时由框架注入；子命令必非 None，主命令为 None
        self._parent = parent
        self.arguments: list[Argument] = []
        self.subcommands: list[Command[Any]] = []
        self._discover_subcommands()
        self.declare()

    @property
    def parent(self) -> ParentT:
        """父命令实例（子命令必非 None，可放心访问父命令方法）。"""
        if self._parent is None:
            raise CommandError('Current command has no parent command!')
        return self._parent

    # ===== 声明 =====

    def declare(self) -> None:
        """覆写以注册参数与子命令。"""

    def register_arg(
        self,
        name: str,
        value_type: Any = str,
        *,
        required: bool = True,
        default: Any = UNSET,
        description: str = '',
        multi: bool = False,
    ) -> Argument:
        """注册一个参数。"""
        argument = Argument(name, value_type, required, default, description, multi)
        self.arguments.append(argument)
        return argument

    def register_option(
        self,
        name: str,
        value_type: Any = str,
        *,
        default: Any = None,
        description: str = '',
        multi: bool = False,
    ) -> Argument:
        """注册一个可选参数。"""
        return self.register_arg(
            name,
            value_type,
            required=False,
            default=default,
            description=description,
            multi=multi,
        )

    def register_subcommand(self, subcommand: 'Command[Any]') -> 'Command[Any]':
        """显式注册一个子命令。"""
        self.subcommands.append(subcommand)
        return subcommand

    def _discover_subcommands(self) -> None:
        """自动发现嵌套的 SubCommand 子类并实例化，parent 指向自身。"""
        for _, member in inspect.getmembers(self.__class__, inspect.isclass):
            if member is SubCommand or not issubclass(member, SubCommand):
                continue
            if inspect.isabstract(member):
                continue
            self.subcommands.append(member(self))

    # ===== 查询 =====

    def find_argument(self, name: str) -> Argument | None:
        for argument in self.arguments:
            if argument.name == name:
                return argument
        return None

    def find_subcommand(self, name: str) -> 'Command[Any] | None':
        for subcommand in self.subcommands:
            if subcommand.name == name:
                return subcommand
        return None

    # ===== 处理器 =====

    async def handler(self, *args, **kwargs) -> AsyncIterable | str | bytes | list | None:
        """
        覆写以处理命令，直接返回要发送的消息内容：
                - 字符串 / 图片字节 / 消息片段列表：框架统一发送
                - 异步迭代器（async generator）：逐项收集后由框架转成多行文本发送，
                  此时 `return` 仅做提前跳出函数用，不承载要发送的消息
                - None：不发送。
        """
        return None

    async def image_handler(self, *args, **kwargs) -> bytes | None:
        """覆写以提供图片模式下渲染的 PNG 字节，由框架发送。"""
        return None


class SubCommand(Command[ParentT]):
    """
    子命令基类：嵌套声明于父命令类内，parent 指向父命令实例。

        为获得父命令的方法提示，请用泛型标注父类型：
        `class Check(SubCommand['AboutCommand'])`。不标注时退化为基础 Command 提示。
    """


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


def discover_commands(module) -> list[Command[Any]]:
    """扫描模块中非抽象、非 SubCommand 的 Command 子类并实例化。"""
    commands = []
    for _, member in inspect.getmembers(module, inspect.isclass):
        if member is Command or member is SubCommand or not issubclass(member, Command):
            continue
        if issubclass(member, SubCommand) or inspect.isabstract(member):
            continue
        commands.append(member())
    return commands


# ===== 命令管理器 =====


class CommandManager:
    """统一收集并构建所有命令 matcher。"""

    command_id_separator = ':'

    def __init__(self) -> None:
        self._built = False
        self._matchers: list[Any] = []
        # 稳定 command_id -> 命令实例
        self._commands: dict[str, Command[Any]] = {}

    # ----- 注册阶段 -----

    def register_command(self, command: Command, command_id: str, *, override: bool = False) -> None:
        """
        登记一个命令实例（内置或扩展）。

                `override=True` 时允许以同名 `command_id` **取代**已登记的命令（用于指令
                扩展覆盖内置命令）；否则重复 `command_id` 视为冲突并报错。
        """
        if self._built:
            raise CommandError('Command manager already built, no more commands can be registered!')
        if command_id in self._commands:
            if not override:
                raise CommandError(f'Command {command_id} registered twice, conflict rejected!')
            logger.info(f'Command {command_id} has been overridden.')
        self._commands[command_id] = command

    def get_command(self, command_id: str) -> Command[Any] | None:
        return self._commands.get(command_id)

    def get_command_nodes(self) -> dict[str, Command[Any]]:
        """返回全部已登记命令：稳定 command_id -> 命令实例。"""
        return dict(self._commands)

    # ----- 校验阶段 -----

    def _validate_node(self, command: Command[Any], extension_id: str, path: list[str]) -> None:
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
                raise CommandFieldError(f'{_format_path(extension_id, argument_path)} optional argument must provide a default value!')

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
        for command_id, command in self._commands.items():
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

    def _build_args(self, command: Command[Any]) -> Args:
        """
        将参数定义转换为 Alconna Args。

                可选参数标记为可选（`name?`）。仅当声明了非 None 的 `default` 时才把它
                直接注入 Alconna，让 Alconna 在用户未提供时填充 `Match.result`；
                `default` 为 None 或未声明时不注入，避免 Alconna 把默认值塞进
                `all_matched_args` 导致 `Match.available` 恒为 True（无法区分「用户显式
                提供」与「走默认」）。因此 `default=None` 的可选参数 `available` 仍准确。
        """
        args = Args()
        for argument in command.arguments:
            value_type = argument._resolved_type()
            if argument.required:
                args.add(argument.name, value=value_type)
            elif argument.default is not UNSET and argument.default is not None:
                args.add(f'{argument.name}?', value=value_type, default=argument.default)
            else:
                args.add(f'{argument.name}?', value=value_type)
        return args

    def _build_subcommand(self, subcommand: Command[Any]) -> Subcommand:
        """将子命令实例递归转换为 Alconna Subcommand（支持嵌套子命令）。"""
        nested = [self._build_subcommand(sub) for sub in subcommand.subcommands]
        return Subcommand(
            subcommand.name,
            self._build_args(subcommand),
            *nested,
            help_text=subcommand.description or None,
        )

    def _build_matcher(self, command: Command[Any]) -> None:
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

    def _assign_subcommand(self, matcher, subcommand: Command[Any], path: str) -> None:
        """递归注册子命令分派处理器，路径用点路径（如 `superusers.add`）。"""
        for nested in subcommand.subcommands:
            self._assign_subcommand(matcher, nested, f'{path}.{nested.name}')
        matcher.assign(path)(self._route(matcher, subcommand.image_handler, subcommand.handler, subcommand))

    @staticmethod
    def _route(matcher, image_handler, handler: Handler, command: Command[Any]) -> Handler:
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
        target = (
            image_handler if config.image.mode and type(command).image_handler is not Command.image_handler else handler
        )

        @wraps(target)
        async def dispatched(*args, **kwargs):
            try:
                # 异步生成器：不 await，逐项收集后转多行文本发送
                if inspect.isasyncgenfunction(target):
                    await matcher.finish(await turn_message_text(target(*args, **kwargs)))
                    return
                result = await target(*args, **kwargs)
                if result is None:
                    return
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

    def build(self) -> list:
        """校验全部命令并构建 matcher，任一失败则整体失败。"""
        if self._built:
            return self._matchers
        self.validate()
        for command in self._commands.values():
            self._build_matcher(command)
        self._built = True
        return self._matchers


# 全局单例
command_manager = CommandManager()
