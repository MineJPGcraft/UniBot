"""内置扩展：命令帮助指令。"""

from typing import override

from nonebot_plugin_alconna import Match

from Scripts.Extensions import Command, Extension, command_manager
from Scripts.Messages import messages
from Scripts.Utils import turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Help', name=messages.builtin_extensions.help, version='1.0.0', types=('command',))


def get_enabled_nodes() -> list[Command]:
    """获取全部已登记的命令节点（内置 builtin: 与扩展 extension: 前缀）。"""
    return list(command_manager.get_command_nodes().values())


def get_node(name: str) -> Command | None:
    """从已登记命令实例中查找指定名称的命令。"""
    for command in get_enabled_nodes():
        if command.name == name:
            return command
    return None


def gen_usage(command: Command) -> str:
    """根据结构化命令自动生成用法字符串（含参数），统一带 `/` 前缀。"""
    parts = [f'/{command.name}']
    for argument in command.arguments:
        display = f'<{argument.name}>' if argument.required else f'[{argument.name}]'
        parts.append(display)
    return ' '.join(parts)


def gen_path_usage(path: list[str], command: Command) -> str:
    """生成子命令完整路径用法，如 `/bot superusers add <target>`。"""
    parts = [f'/{" ".join(path)}']
    for argument in command.arguments:
        display = f'<{argument.name}>' if argument.required else f'[{argument.name}]'
        parts.append(display)
    return ' '.join(parts)


def node_args(command: Command) -> list[dict]:
    """提取命令参数（含描述）用于图片渲染。"""
    return [
        {'name': argument.name, 'notice': argument.description}
        for argument in command.arguments
        if argument.description
    ]


def node_arg_rows(command: Command) -> list[dict]:
    """提取命令全部参数的结构化行（含必填标记），供图片模板渲染。"""
    return [
        {
            'name': argument.name,
            'notice': argument.description,
            'required': argument.required,
            'required_text': (
                messages.commands.help.arg_required if argument.required else messages.commands.help.arg_optional
            ),
        }
        for argument in command.arguments
    ]


def _walk_subcommands(subcommands: list[Command], path_prefix: list[str], indent: str = '') -> list[str]:
    """递归展开子命令树为展示行（完整路径 + 嵌套子命令 + 参数描述）。"""
    lines: list[str] = []
    for index, subcommand in enumerate(subcommands):
        is_last = index == len(subcommands) - 1
        branch = '└─' if is_last else '├─'
        continuation = '    ' if is_last else '│   '
        path = path_prefix + [subcommand.name]
        description = f' — {subcommand.description}' if subcommand.description else ''
        lines.append(f'{indent}{branch} {gen_path_usage(path, subcommand)}{description}')
        for argument in subcommand.arguments:
            if argument.description:
                arg_line = messages.commands.help.arg_line.format(name=argument.name, notice=argument.description)
                lines.append(f'{indent}{continuation}    {arg_line}')
        if subcommand.subcommands:
            lines.extend(_walk_subcommands(subcommand.subcommands, path, f'{indent}{continuation}    '))
    return lines


def _collect_subcommand_rows(subcommands: list[Command], path_prefix: list[str], depth: int = 0) -> list[dict]:
    """递归收集子命令树为结构化行（完整路径用法、描述、层级与参数），供图片模板渲染。"""
    rows: list[dict] = []
    for subcommand in subcommands:
        path = path_prefix + [subcommand.name]
        rows.append(
            {
                'usage': gen_path_usage(path, subcommand),
                'description': subcommand.description or '',
                'depth': depth,
                'args': [row for row in node_arg_rows(subcommand) if row['notice']],
            }
        )
        rows.extend(_collect_subcommand_rows(subcommand.subcommands, path, depth + 1))
    return rows


@extension.register_command
class HelpCommand(Command):
    """查看所有可用命令的帮助信息。"""

    name = 'help'
    description = messages.commands.help.description
    usage = messages.commands.help.usage

    @override
    def declare(self) -> None:
        self.register_option('command', str, description=messages.commands.help.option_command)

    @override
    async def handler(self, command: Match[str]):
        if command.available:
            return await turn_message_text(self.detailed_handler(command.result))
        return await turn_message_text(self.help_handler())

    @override
    async def image_handler(self, command: Match[str]) -> bytes:
        """渲染帮助信息为图片，返回 PNG 字节（由框架在图像模式发送）。"""
        if command.available:
            detail = self.get_command_detail(command.result)
            return await extension.render_image('Help', (600, 0), context={'detail': detail, 'commands': None})
        commands = self.get_commands_list()
        return await extension.render_image('Help', (600, 0), context={'detail': None, 'commands': commands})

    def get_commands_list(self) -> list[dict]:
        """构建命令列表数据用于图片渲染。"""
        commands = []
        for command in get_enabled_nodes():
            usage = command.usage or gen_usage(command)
            description = command.description or ''
            commands.append(
                {
                    'usage': usage,
                    'description': description,
                    'subcommands': _collect_subcommand_rows(command.subcommands, [command.name]),
                }
            )
        return commands

    def get_command_detail(self, name: str) -> dict | None:
        """构建命令详情数据用于图片渲染。"""
        command = get_node(name)
        if command is None:
            return None
        return {
            'name': name,
            'aliases': list(command.aliases),
            'usage': command.usage or gen_usage(command),
            'description': command.description or '',
            'args': node_arg_rows(command),
            'subcommands': _collect_subcommand_rows(command.subcommands, [command.name]),
        }

    def help_handler(self):
        yield messages.commands.help.title
        for command in get_enabled_nodes():
            usage = command.usage or gen_usage(command)
            description = command.description or ''
            yield f'    {usage} — {description}'
            yield from _walk_subcommands(command.subcommands, [command.name], '    ')
        yield messages.commands.help.footnote

    def detailed_handler(self, name: str):
        command = get_node(name)
        if command is None:
            yield messages.commands.help.not_found.format(name=name)
            return
        yield messages.commands.help.detail_title.format(name=name)
        yield f'    {messages.commands.help.detail_usage.format(usage=command.usage or gen_usage(command))}'
        if command.description:
            yield f'    {messages.commands.help.detail_description.format(description=command.description)}'
        notices = node_args(command)
        if notices:
            yield f'    {messages.commands.help.detail_args_title}'
            for arg in notices:
                yield f'        {messages.commands.help.arg_line.format(name=arg["name"], notice=arg["notice"])}'
        if not command.subcommands:
            return
        yield f'    {messages.commands.help.detail_subcommands_title}'
        yield from _walk_subcommands(command.subcommands, [command.name], '        ')
