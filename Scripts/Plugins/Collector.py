"""数据统计插件：监听收发消息，统计机器人发言总量、场景分布与活跃群聊。"""

from typing import Any

from nonebot import get_driver, on_message
from nonebot.adapters import Bot
from nonebot.plugin import PluginMetadata
from nonebot_plugin_uninfo import SceneType, SupportScope, Uninfo

from Scripts.Logging import logger
from Scripts.Managers import statistics_manager, task_manager
from Scripts.Utils import get_platform_name

__plugin_meta__ = PluginMetadata(
    name='数据统计',
    description='统计机器人发言总数、各场景消息量与活跃群聊，供 WebUI 统计页展示。',
    usage='自动在后台收集数据，无需手动触发；可在 WebUI「统计」页查看。',
)

driver = get_driver()

# 群聊类会话场景（频道文本场景同样按群聊口径统计）
GROUP_SCENES = (SceneType.GROUP, SceneType.GUILD, SceneType.CHANNEL_TEXT)

# 判定为「发送消息」的 API 名称排除项（媒体上传、分片与撤回等不算发言）
SEND_API_EXCLUDED = (
    'upload',
    'file',
    'prepare',
    'finish',
    'recall',
    'delete',
    'react',
    'emoji',
    'keyboard',
    'markdown',
)
# 发送目标为群聊场景的参数键（跨适配器宽松匹配）
GROUP_TARGET_KEYS = ('group_id', 'group_openid', 'guild_id', 'channel_id')
# 发送目标为私聊场景的参数键
PRIVATE_TARGET_KEYS = ('user_id', 'openid', 'chat_id')

# 定时落盘间隔（秒），仅在存在未写入的增量时写盘
SAVE_INTERVAL_SECONDS = 120


def is_message_send_api(api_name: str) -> bool:
    """判断 API 名称是否代表一次向外发送消息。"""
    lowered = api_name.lower()
    if lowered.startswith(('get_', 'set_')) or any(marker in lowered for marker in SEND_API_EXCLUDED):
        return False
    return 'send' in lowered or 'message' in lowered or lowered.startswith('post_')


def extract_target_kind(data: dict[str, Any]) -> str:
    """从 API 调用参数推断发送目标场景类型。"""
    if any(data.get(key) for key in GROUP_TARGET_KEYS):
        return 'group'
    if any(data.get(key) for key in PRIVATE_TARGET_KEYS):
        return 'private'
    return 'unknown'


@Bot.on_called_api
async def count_sent_message(
    bot: Bot, exception: Exception | None, api: str, data: dict[str, Any], result: Any
) -> None:
    """API 调用后钩子：统计一次成功的向外发消息。"""
    if exception is not None or not is_message_send_api(api):
        return
    statistics_manager.record_sent(extract_target_kind(data))


@driver.on_startup
async def load_statistics_on_startup() -> None:
    """启动时加载历史统计数据并登记定时落盘任务。"""
    statistics_manager.load()
    task_manager.add('statistics-autosave', save_dirty_statistics, SAVE_INTERVAL_SECONDS)


async def save_dirty_statistics() -> None:
    """把未写入磁盘的统计增量持久化一次。"""
    if statistics_manager.dirty:
        try:
            await statistics_manager.save()
        except Exception as error:
            logger.warning(f'Failed to save statistics data: {error}')


@driver.on_shutdown
async def save_statistics_on_shutdown() -> None:
    """关闭时持久化统计数据。"""
    if statistics_manager.dirty:
        await statistics_manager.save()


message_watcher = on_message(priority=0, block=False)


@message_watcher.handle()
async def count_received_message(session: Uninfo) -> None:
    """统计每条收到的平台消息及其群聊活跃度。"""
    platform_name = get_platform_name(session.scope)
    group_key = group_name = None
    if session.scene.type in GROUP_SCENES and session.scene.id:
        group_key = f'{SupportScope(session.scope).name}:{session.scene.id}'
        group_name = session.scene.name or None
    statistics_manager.record_received(platform_name, group_key=group_key, group_name=group_name)
