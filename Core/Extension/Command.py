"""
声明式命令抽象层：扩展作者继承的 `Command` / `SubCommand` 基类与参数模型。

命令以类声明：继承 Command 定义主命令，类属性声明元数据，覆写 declare()
注册参数与子命令，覆写 handler()/image_handler() 提供业务逻辑。子命令通过
嵌套 SubCommand 类的形式声明，框架自动发现并实例化，父命令实例经 `parent`
访问（仅 SubCommand 持有）。命令树到 Alconna matcher 的构建见 `Runtime/Managers/Command.py`。
"""

import inspect
import re
from abc import ABC
from collections.abc import AsyncIterable, Awaitable, Callable
from typing import Any, Generic, TypeVar

from arclet.alconna import Args, MultiVar

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

    def to_alconna_args(self) -> Args:
        """
        把参数定义转换为 Alconna Args。

            可选参数标记为可选（`name?`）。仅当声明了非 None 的 `default` 时才把它
            直接注入 Alconna，让 Alconna 在用户未提供时填充 `Match.result`；
            `default` 为 None 或未声明时不注入，避免 Alconna 把默认值塞进
            `all_matched_args` 导致 `Match.available` 恒为 True（无法区分「用户显式
            提供」与「走默认」）。因此 `default=None` 的可选参数 `available` 仍准确。
        """
        args = Args()
        if self.required:
            args.add(self.name, value=self._resolved_type())
        elif self.default is not UNSET and self.default is not None:
            args.add(f'{self.name}?', value=self._resolved_type(), default=self.default)
        else:
            args.add(f'{self.name}?', value=self._resolved_type())
        return args


# ===== 命令基类 =====


class Command(ABC):
    """
    命令基类：子类继承并声明元数据，覆写 declare() 注册参数与子命令，
        覆写 handler()/image_handler() 提供业务逻辑。子命令通过嵌套 SubCommand
        类的形式声明，框架自动发现并实例化。
    """

    name: str = ''
    description: str = ''
    usage: str | None = None
    aliases: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.arguments: list[Argument] = []
        self.subcommands: list[SubCommand[Any]] = []
        self._discover_subcommands()
        self.declare()

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

    def register_subcommand(self, subcommand: 'SubCommand[Any]') -> 'SubCommand[Any]':
        """显式注册一个子命令。"""
        self.subcommands.append(subcommand)
        return subcommand

    def _discover_subcommands(self) -> None:
        """自动发现嵌套的 SubCommand 子类并实例化，把 parent 指向自身。"""
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

    def find_subcommand(self, name: str) -> 'SubCommand[Any] | None':
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


# 子命令的父命令类型参数，默认退化为 Command
ParentT = TypeVar('ParentT', bound=Command)


class SubCommand(Command, Generic[ParentT]):
    """
    子命令基类：嵌套声明于父命令类内，构造时由框架传入父命令实例（`parent`）。

        父命令类型经泛型参数标注可获得完整类型提示：`class Check(SubCommand['AboutCommand'])`；
        不标注时 `parent` 退化为基础 `Command`。
    """

    def __init__(self, parent: ParentT) -> None:
        self._parent = parent
        super().__init__()

    @property
    def parent(self) -> ParentT:
        """父命令实例。"""
        return self._parent
