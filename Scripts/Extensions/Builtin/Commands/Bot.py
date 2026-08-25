"""内置扩展：机器人管理指令。"""

import asyncio
from typing import TypeAlias, override

from nonebot_plugin_alconna import At
from nonebot_plugin_uninfo import Uninfo

from Scripts.Config import config
from Scripts.Extensions import Command, Extension, SubCommand, extension_manager
from Scripts.Logging import exception_logger, logger
from Scripts.Managers import config_manager, version_manager
from Scripts.Messages import messages
from Scripts.Process import is_watchdog_process, request_restart
from Scripts.Utils import get_permission, turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Bot', name=messages.builtin_extensions.bot, version='1.0.0', types=('command',))

# 固定链接与群号信息（语言无关，文案模板见消息包 [commands.bot]）
_DOCUMENT_URL = 'https://bot.mcjpg.dev/'
_REPO_URL = 'https://github.com/MineJPGcraft/UniBot'
_INVITE_GROUP = '962802248'


@extension.register_command
class BotCommand(Command):
    """管理机器人（超级用户 / 关于信息 / 检查更新 / 更新 / 重启）。"""

    name = 'bot'
    description = messages.commands.bot.description
    usage = messages.commands.bot.usage

    # ===== 公用处理函数（被多个子命令共用，定义在父命令类下） =====

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

    async def _delayed_restart(self) -> None:
        """延迟触发重启，确保回复消息先完成发送。"""
        await asyncio.sleep(1)
        request_restart()

    class Superusers(SubCommand['BotCommand']):
        """管理超级用户。"""

        name = 'superusers'
        description = messages.commands.bot.superusers_desc

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

        class Add(SubCommand['BotSuperusers']):
            """添加超级用户。"""

            name = 'add'
            description = messages.commands.bot.superusers_add_desc

            @override
            def declare(self) -> None:
                self.register_arg('target', At | str, description=messages.commands.bot.target_arg)

            @override
            async def handler(self, session: Uninfo, target: At | str):
                if not get_permission(session):
                    return messages.commands.bot.no_permission
                return self.parent.update_superusers(target, remove=False)

        class Remove(SubCommand['BotSuperusers']):
            """移除超级用户。"""

            name = 'remove'
            description = messages.commands.bot.superusers_remove_desc

            @override
            def declare(self) -> None:
                self.register_arg('target', At | str, description=messages.commands.bot.target_arg)

            @override
            async def handler(self, session: Uninfo, target: At | str):
                if not get_permission(session):
                    return messages.commands.bot.no_permission
                return self.parent.update_superusers(target, remove=True)

    class About(SubCommand['BotCommand']):
        """查看关于信息。"""

        name = 'about'
        description = messages.commands.bot.about_desc
        usage = messages.commands.bot.about_usage

        @override
        async def handler(self):
            return await turn_message_text(self.about_handler())

        @override
        async def image_handler(self) -> bytes:
            """渲染关于信息为图片，返回 PNG 字节（由框架在图像模式发送）。"""
            return await self.parent._render_about()

        async def about_handler(self):
            version_line = (
                messages.commands.bot.version_outdated.format(current=version_manager.version)
                if version_manager.check_update()
                else messages.commands.bot.version_latest.format(current=version_manager.version)
            )
            yield version_line
            yield messages.commands.bot.about_document.format(url=_DOCUMENT_URL)
            yield messages.commands.bot.about_repo.format(url=_REPO_URL)
            yield messages.commands.bot.about_invite.format(group=_INVITE_GROUP)

    class Check(SubCommand['BotCommand']):
        """检测是否有新版本。"""

        name = 'check'
        description = messages.commands.bot.check_desc

        @override
        async def handler(self):
            return await turn_message_text(self.check_handler())

        @override
        async def image_handler(self) -> bytes:
            """拉取最新版本后渲染关于信息为图片（由框架在图像模式发送）。"""
            await version_manager.fetch_latest()
            return await self.parent._render_about()

        async def check_handler(self):
            if await version_manager.fetch_latest():
                if version_manager.check_update():
                    yield messages.commands.bot.check_new_version.format(
                        latest=version_manager.latest_version, current=version_manager.version
                    )
                    return
                yield messages.commands.bot.check_up_to_date.format(version=version_manager.version)
                return
            yield messages.commands.bot.check_failed

    class Update(SubCommand['BotCommand']):
        """从 GitHub Release 更新机器人到最新版本。"""

        name = 'update'
        description = messages.commands.bot.update_desc

        @override
        async def handler(self, session: Uninfo):
            if not get_permission(session):
                return messages.commands.bot.no_permission
            return await self.update_handler()

        async def update_handler(self) -> str:
            """从 GitHub Release 下载最新代码并重启机器人，完成更新。"""
            if not is_watchdog_process():
                return messages.commands.bot.update_watchdog_required
            error_message = await version_manager.update()
            if error_message:
                return messages.commands.bot.update_failed.format(error=error_message)
            logger.success('Update succeeded, preparing to restart the bot.')
            asyncio.create_task(self.parent._delayed_restart())
            return messages.commands.bot.update_success

    class Restart(SubCommand['BotCommand']):
        """重启机器人。"""

        name = 'restart'
        description = messages.commands.bot.restart_desc

        @override
        async def handler(self, session: Uninfo):
            if not get_permission(session):
                return messages.commands.bot.no_permission
            return self.restart_handler()

        def restart_handler(self) -> str:
            """请求守护进程重启机器人。"""
            if not is_watchdog_process():
                return messages.commands.bot.restart_watchdog_required
            asyncio.create_task(self.parent._delayed_restart())
            return messages.commands.bot.restarting

    class Reload(SubCommand['BotCommand']):
        """热重载扩展。"""

        name = 'reload'
        description = messages.commands.bot.reload_desc

        @override
        async def handler(self, session: Uninfo):
            if not get_permission(session):
                return messages.commands.bot.no_permission
            try:
                await extension_manager.reload()
            except Exception as error:
                exception_logger.error(f'Extension reload failed: {error}')
                return messages.commands.bot.reload_failed.format(error=error)
            return messages.commands.bot.reload_success


# 深层子命令的父命令类型别名：供 SubCommand 泛型引用，获得完整的 parent 类型提示
BotSuperusers: TypeAlias = BotCommand.Superusers
