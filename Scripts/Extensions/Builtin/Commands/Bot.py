"""内置扩展：机器人管理指令。"""

import asyncio
from typing import TypeAlias, override

from nonebot_plugin_alconna import At
from nonebot_plugin_uninfo import Uninfo

from Scripts.Config import config
from Scripts.Extensions import Command, Extension, SubCommand
from Scripts.Logging import logger
from Scripts.Managers import config_manager, version_manager
from Scripts.Messages import messages
from Scripts.Process import is_watchdog_process, request_restart
from Scripts.Utils import get_permission, turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Bot', name='机器人管理', version='1.0.0', types=('command',))

# 关于信息固定文本（不依赖 messages.toml）
_DOCUMENT_LINE = '项目文档：https://bot.mcjpg.dev/'
_REPO_LINE = '项目地址 https://github.com/MineJPGcraft/UniBot'
_INVITE_LINE = '欢迎加入 QQ 交流群 962802248，对这个项目感兴趣不妨点个 Star 吧！'


@extension.register_command
class BotCommand(Command):
    """管理机器人（超级用户 / 关于信息 / 检查更新 / 更新 / 重启）。"""

    name = 'bot'
    description = '管理机器人。'
    usage = '/bot <superusers|about|check|update|restart>'

    class Superusers(SubCommand['BotCommand']):
        """管理超级用户。"""

        name = 'superusers'
        description = '管理超级用户'

        class Add(SubCommand['BotSuperusers']):
            """添加超级用户。"""

            name = 'add'
            description = '添加超级用户'

            @override
            def declare(self) -> None:
                self.register_arg('target', At | str, description='目标（@用户 / 用户ID）')

            @override
            async def handler(self, session: Uninfo, target: At | str):
                if not get_permission(session):
                    return messages.commands.bot.no_permission
                return self.parent.parent.update_superusers(target, remove=False)

        class Remove(SubCommand['BotSuperusers']):
            """移除超级用户。"""

            name = 'remove'
            description = '移除超级用户'

            @override
            def declare(self) -> None:
                self.register_arg('target', At | str, description='目标（@用户 / 用户ID）')

            @override
            async def handler(self, session: Uninfo, target: At | str):
                if not get_permission(session):
                    return messages.commands.bot.no_permission
                return self.parent.parent.update_superusers(target, remove=True)

    class About(SubCommand['BotCommand']):
        """查看关于信息。"""

        name = 'about'
        description = '查看关于信息。'
        usage = '/bot about'

        @override
        async def handler(self):
            return await turn_message_text(self.parent.about_handler())

        @override
        async def image_handler(self) -> bytes:
            """渲染关于信息为图片，返回 PNG 字节（由框架在图像模式发送）。"""
            return await self.parent._render_about()

    class Check(SubCommand['BotCommand']):
        """检测是否有新版本。"""

        name = 'check'
        description = '检测是否有新版本'

        @override
        async def handler(self):
            return await turn_message_text(self.parent.check_handler())

        @override
        async def image_handler(self) -> bytes:
            """拉取最新版本后渲染关于信息为图片（由框架在图像模式发送）。"""
            await version_manager.fetch_latest()
            return await self.parent._render_about()

    class Update(SubCommand['BotCommand']):
        """从 GitHub Release 更新机器人到最新版本。"""

        name = 'update'
        description = '更新机器人到最新版本'

        @override
        async def handler(self, session: Uninfo):
            if not get_permission(session):
                return messages.commands.bot.no_permission
            return await self.parent.update_handler()

    class Restart(SubCommand['BotCommand']):
        """重启机器人。"""

        name = 'restart'
        description = '重启机器人'

        @override
        async def handler(self, session: Uninfo):
            if not get_permission(session):
                return messages.commands.bot.no_permission
            return self.parent.restart_handler()

    # ===== 超级用户管理 =====

    def update_superusers(self, target: At | str, remove: bool) -> str:
        """增删超级用户：写回 .env 持久化并热更新内存。"""
        user_id = str(target.target) if isinstance(target, At) else str(target)
        current = list(config.superusers)
        if remove:
            if user_id not in current:
                return messages.commands.bot.not_found.format(value=user_id, name='superusers')
            current.remove(user_id)
        else:
            if user_id in current:
                return messages.commands.bot.already_added.format(value=user_id, name='superusers')
            current.append(user_id)
        try:
            config_manager.update_env({'SUPERUSERS': current})
        except Exception as error:
            logger.warning(f'Failed to write .env: {error}')
            return messages.commands.bot.write_failed
        # 热更新内存，使本项目权限检查立即生效（框架权限需重启后完全生效）
        config.superusers = current
        action = messages.commands.bot.remove_success if remove else messages.commands.bot.add_success
        return action.format(value=user_id, name='superusers') + messages.commands.bot.restart_hint

    # ===== 关于信息 =====

    async def about_handler(self):
        version_line = (
            f'当前版本为 {version_manager.version}，发现新版本，请及时更新！'
            if version_manager.check_update()
            else f'当前版本为 {version_manager.version}，已是最新版本！'
        )
        yield version_line
        yield _DOCUMENT_LINE
        yield _REPO_LINE
        yield _INVITE_LINE

    async def check_handler(self):
        if await version_manager.fetch_latest():
            if version_manager.check_update():
                yield f'发现新版本 {version_manager.latest_version}，当前版本为 {version_manager.version}，请及时更新！'
                return
            yield f'当前已是最新版本 {version_manager.version}！'
            return
        yield '检测失败，请检查网络稍后再试！'

    async def _render_about(self) -> bytes:
        """渲染当前版本信息的模板图片。"""
        return await extension.render_image(
            'About',
            (500, 0),
            context={
                'version': version_manager.version,
                'has_update': version_manager.check_update(),
            },
        )

    # ===== 更新与重启 =====

    def restart_handler(self) -> str:
        """请求守护进程重启机器人。"""
        if not is_watchdog_process():
            return '机器人未通过 Watchdog 启动，无法自动重启！'
        asyncio.create_task(self._delayed_restart())
        return '机器人正在重启，请稍候……'

    async def update_handler(self) -> str:
        """从 GitHub Release 下载最新代码并重启机器人，完成更新。"""
        if not is_watchdog_process():
            return '机器人未通过 Watchdog 启动，无法自动更新！'
        error_message = await version_manager.update()
        if error_message:
            return f'更新失败：{error_message}'
        logger.success('Update succeeded, preparing to restart the bot.')
        asyncio.create_task(self._delayed_restart())
        return '更新成功，机器人正在重启，请稍候……'

    async def _delayed_restart(self) -> None:
        """延迟触发重启，确保回复消息先完成发送。"""
        await asyncio.sleep(1)
        request_restart()


# 深层子命令的父命令类型别名：供 SubCommand 泛型引用，获得完整的 parent 类型提示
BotSuperusers: TypeAlias = BotCommand.Superusers
