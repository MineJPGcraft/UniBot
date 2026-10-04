"""内置扩展：控制台命令指令。"""

from typing import override

from nonebot_plugin_alconna import Match
from nonebot_plugin_uninfo import Uninfo

from Core.Config import config
from Core.Extension import Command, Extension
from Core.I18n import i18n_deferred, text
from Core.RuntimeState import runtime_state
from Core.Utils import get_permission, strip_minecraft_color, turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Command', name=i18n_deferred('builtin.command.name'), version='1.0.0', types=('command',))


@extension.register_command
class CommandCommand(Command):
    """向指定服务器发送控制台命令。"""

    name = 'command'
    description = i18n_deferred('core.commands.command.description')
    usage = i18n_deferred('core.commands.command.usage')

    @override
    def declare(self) -> None:
        self.register_arg('server', str, description=i18n_deferred('core.commands.command.arg_server'))
        self.register_arg('command', str, description=i18n_deferred('core.commands.command.arg_command'), multi=True)

    @override
    async def handler(self, session: Uninfo, server: Match[str], command: Match[list[str]]):
        if not get_permission(session):
            return text('core.commands.command.no_permission')
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
        server_service = runtime_state.server_service
        if server_service is None:
            yield text('core.commands.command.no_server')
            return
        if not (parsed_command := self.parse_command(command)):
            yield text('core.commands.command.command_forbidden', command=command)
            return
        if server_flag == '*':
            if not server_service.servers:
                yield text('core.commands.command.no_server')
                return
            yield text('core.commands.command.send_all_title')
            results = await server_service.execute(parsed_command)
            for name, result in results.items():
                if result is None:
                    yield text('core.commands.command.send_failed', name=name)
                    continue
                reply = result or text('core.commands.command.no_return')
                yield text('core.commands.command.send_result', name=name, result=reply)
            return
        bot = server_service.get_server(server_flag)
        if bot is None:
            yield text('core.commands.command.server_not_found', server_flag=server_flag)
            return
        try:
            result = await bot.send_rcon_command(command=parsed_command)
            reply = strip_minecraft_color(result) if result else text('core.commands.command.no_return')
            yield text('core.commands.command.send_success', server=bot.self_id, result=reply)
        except Exception as error:
            yield text('core.commands.command.send_error', server_flag=server_flag, error=error)
