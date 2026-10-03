"""内置扩展：控制台命令指令。"""

from typing import override

from nonebot_plugin_alconna import Match
from nonebot_plugin_uninfo import Uninfo

from Scripts import Globals
from Scripts.Config import config
from Scripts.Extensions import Command, Extension
from Scripts.Messages import messages
from Scripts.Utils import get_permission, strip_minecraft_color, turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Command', name=messages.builtin_extensions.command, version='1.0.0', types=('command',))


@extension.register_command
class CommandCommand(Command):
    """向指定服务器发送控制台命令。"""

    name = 'command'
    description = messages.commands.command.description
    usage = messages.commands.command.usage

    @override
    def declare(self) -> None:
        self.register_arg('server', str, description=messages.commands.command.arg_server)
        self.register_arg('command', str, description=messages.commands.command.arg_command, multi=True)

    @override
    async def handler(self, session: Uninfo, server: Match[str], command: Match[list[str]]):
        if not get_permission(session):
            return messages.commands.command.no_permission
        command_string = ' '.join(command.result)
        return await turn_message_text(self.command_handler(server.result, command_string))

    def parse_command(self, command: str):
        """按黑白名单过滤允许发送的控制台命令。"""
        if config.command_minecraft_whitelist:
            if any(command.startswith(item) for item in config.command_minecraft_whitelist):
                return command
            return None
        if any(command.startswith(item) for item in config.command_minecraft_blacklist):
            return None
        return command

    async def command_handler(self, server_flag, command):
        server_service = Globals.server_service
        if server_service is None:
            yield messages.commands.command.no_server
            return
        if not (parsed_command := self.parse_command(command)):
            yield messages.commands.command.command_forbidden.format(command=command)
            return
        if server_flag == '*':
            if not server_service.servers:
                yield messages.commands.command.no_server
                return
            yield messages.commands.command.send_all_title
            results = await server_service.execute(parsed_command)
            for name, result in results.items():
                if result is None:
                    yield messages.commands.command.send_failed.format(name=name)
                    continue
                reply = result or messages.commands.command.no_return
                yield messages.commands.command.send_result.format(name=name, result=reply)
            return
        bot = server_service.get_server(server_flag)
        if bot is None:
            yield messages.commands.command.server_not_found.format(server_flag=server_flag)
            return
        try:
            result = await bot.send_rcon_command(command=parsed_command)
            reply = strip_minecraft_color(result) if result else messages.commands.command.no_return
            yield messages.commands.command.send_success.format(server=bot.self_id, result=reply)
        except Exception as error:
            yield messages.commands.command.send_error.format(server_flag=server_flag, error=error)
