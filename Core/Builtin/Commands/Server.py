"""内置扩展：服务器列表指令。"""

import asyncio
from typing import override

from Core.Extension import Command, Extension
from Core.I18n import i18n_deferred, text
from Core.RuntimeState import runtime_state
from Core.Utils import turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Server', name=i18n_deferred('builtin.server.name'), version='1.0.0', types=('command',))


@extension.register_command
class ServerCommand(Command):
    """查看已连接的服务器列表及其 CPU / 内存占用。"""

    name = 'server'
    description = i18n_deferred('core.commands.server.description')
    usage = i18n_deferred('core.commands.server.usage')

    @override
    async def handler(self):
        return await turn_message_text(self.server_handler())

    @override
    async def image_handler(self) -> bytes:
        """渲染服务器列表（含占用信息）为图片，返回 PNG 字节（由框架在图像模式发送）。"""
        return await extension.render_image(
            'Server', (500, 0), context={'servers': await self.collect_server_overview()}
        )

    async def collect_server_overview(self) -> list[dict]:
        """并发查询所有服务器状态，组装为带编号与占用信息的展示数据。"""
        server_service = runtime_state.server_service
        if server_service is None:
            return []
        bots = list(server_service.servers.items())
        statuses = await asyncio.gather(*(server_service.get_status(bot) for _, bot in bots))
        return [
            {'name': name, 'index': index, **status} for index, ((name, _), status) in enumerate(zip(bots, statuses))
        ]

    async def server_handler(self):
        servers = await self.collect_server_overview()
        if not servers:
            yield text('core.commands.server.no_server')
            return
        for server in servers:
            if not server['online']:
                yield text('core.commands.server.server_offline_line', index=server['index'], name=server['name'])
                continue
            yield text(
                'core.commands.server.server_line',
                index=server['index'],
                name=server['name'],
                cpu_percent=server['cpu_load'],
                memory_percent=server['memory_percent'],
                memory_used=server['jvm_memory_used'],
                memory_max=server['jvm_memory_max'],
            )
