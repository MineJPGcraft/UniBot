import asyncio
import re
from collections.abc import AsyncIterable, Iterable
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, is_zipfile

from nonebot_plugin_alconna import SupportScope as AlconnaSupportScope
from nonebot_plugin_alconna import Target
from nonebot_plugin_uninfo import SupportScope as UninfoSupportScope

from Scripts.Logging import logger

from .Config import config

# 单个 zip 解压后允许的最大体积（默认 100 MB）
MAX_ARCHIVE_TOTAL = 100 * 1024 * 1024
# 单个 zip 允许的最大文件数量（防御 zip 炸弹）
MAX_ARCHIVE_FILES = 2048

regex = re.compile(r'[A-Z0-9_]+|\.[A-Z0-9_]+', re.IGNORECASE)
minecraft_color_pattern = re.compile(r'§x(?:§[0-9a-f]){6}|§[0-9a-fk-orx]', re.IGNORECASE)
scope_mapping = {
    str(UninfoSupportScope.qq_client): 'QQ',
    str(UninfoSupportScope.qq_api): 'QQ',
    str(UninfoSupportScope.qq_guild): 'QQ',
    str(UninfoSupportScope.telegram): 'Telegram',
    str(UninfoSupportScope.discord): 'Discord',
    str(UninfoSupportScope.dodo): 'DoDo',
    str(UninfoSupportScope.kook): 'Kook',
    str(UninfoSupportScope.wechat): 'WX',
    str(UninfoSupportScope.wecom): 'WX',
    str(UninfoSupportScope.minecraft): 'MC',
}


async def turn_message_text(iterator: AsyncIterable[str] | Iterable[str]) -> str:
    if isinstance(iterator, Iterable):
        return '\n'.join(iterator)
    return '\n'.join([text async for text in iterator])


def strip_minecraft_color(text: str) -> str:
    """去除字符串中的 Minecraft 颜色与格式代码。"""
    return minecraft_color_pattern.sub('', text)


def check_player(player: str) -> bool:
    return len(player) <= 16 and get_player_name(player) == player


def check_message(message: str) -> bool:
    return any(word in message for word in config.sync_sensitive_words)


def get_player_name(name: str) -> str | None:
    if result := regex.search(name):
        return result.group()


def get_platform_name(scope: str) -> str:
    """获取平台的可读名称。"""
    return scope_mapping.get(scope, '未知平台')


async def send_message_to_groups(message: str) -> bool:
    """向配置中的所有平台群组发送消息。"""
    send_tasks = []
    try:
        for group_info in config.message_groups:
            platform, separator, group_id = group_info.partition(':')
            if not separator or not group_id:
                logger.warning(f'Invalid message group config: {group_info}')
                continue
            scope = getattr(AlconnaSupportScope, platform.lower(), None)
            if scope is None:
                logger.warning(f'Unsupported platform type: {platform}, please check the config file.')
                continue
            send_tasks.append(Target.group(group_id, scope).send(message))
        if send_tasks:
            await asyncio.gather(*send_tasks)
        return True
    except Exception as error:
        logger.warning(f'Failed to send group message: {error}')
        return False


def get_permission(session) -> bool:
    """检查用户是否为超级用户或管理员。"""
    uid = str(session.user.id)
    if uid in config.superusers:
        return True
    if config.admin_superusers and session.member and session.member.role:
        return session.member.role.id in ('OWNER', 'ADMINISTRATOR')
    return False


# ===== 安全解压 =====


class ArchiveError(Exception):
    """zip 解压校验失败。"""


def _safe_relative(relative: str) -> Path:
    """校验 zip 内相对路径不越界、非绝对路径，返回规范化 Path。"""
    path = Path(relative)
    if path.is_absolute():
        raise ArchiveError(f'Absolute paths are not allowed in archives: {relative}')
    if '..' in path.parts:
        raise ArchiveError(f'Path traversal is not allowed in archives: {relative}')
    return path


def safe_extract_zip(archive_data: bytes, target_dir: Path) -> None:
    """
    安全解压 zip 到目标目录。

        拒绝绝对路径、`..` 越界、符号链接/硬链接，并限制解压总大小与文件数量。
        任一步校验失败都会抛出 `ArchiveError`，且不向目标目录写入任何文件。
    """
    if not is_zipfile(BytesIO(archive_data)):
        raise ArchiveError('Archive is not a valid zip file!')
    with ZipFile(BytesIO(archive_data)) as zip_file:
        _validate_archive(zip_file)
        zip_file.extractall(target_dir)


def _validate_archive(zip_file: ZipFile) -> None:
    """校验 zip 全部成员：路径安全、符号链接、大小与数量限制。"""
    infos = zip_file.infolist()
    if len(infos) > MAX_ARCHIVE_FILES:
        raise ArchiveError(f'Too many files in archive ({len(infos)} exceeds {MAX_ARCHIVE_FILES}), rejected!')
    total_size = 0
    for info in infos:
        _safe_relative(info.filename)
        mode = info.external_attr >> 16
        if mode & 0o170000 == 0o120000:
            raise ArchiveError(f'Symbolic links are not allowed in archives: {info.filename}')
        if not info.is_dir():
            total_size += info.file_size
            if total_size > MAX_ARCHIVE_TOTAL:
                raise ArchiveError(
                    f'Archive is too large after extraction (exceeds {MAX_ARCHIVE_TOTAL // (1024 * 1024)} MB), rejected!'
                )
    logger.debug(f'Archive validation passed: {len(infos)} files, about {total_size} bytes.')
