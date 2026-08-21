"""认证令牌插件：监听所有平台消息，校验令牌并授权群聊与用户。"""

import hashlib
import time

from nonebot import get_driver, on_message
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule
from nonebot_plugin_alconna.uniseg import UniMsg
from nonebot_plugin_uninfo import SceneType, SupportScope, Uninfo

from Scripts import Globals
from Scripts.Config import config
from Scripts.Logging import logger
from Scripts.Managers import config_manager

TOKEN_LENGTH = 10
"""令牌显示长度（取哈希前 N 位，大写十六进制）。"""

__plugin_meta__ = PluginMetadata(
    name='认证令牌',
    description='监听所有平台消息，校验认证令牌并授权群聊与用户。',
    usage='在任意平台群聊中发送机器人打印的认证令牌即可完成授权。',
)

driver = get_driver()

_group_scenes = (SceneType.GROUP, SceneType.GUILD, SceneType.CHANNEL_TEXT)


@driver.on_startup
async def print_token_on_startup() -> None:
    """启动时打印当前认证令牌。"""
    refresh_token()


def generate_token() -> str:
    """以模块文件路径与当前时间混合计算令牌哈希。"""
    payload = f'{__file__}:{time.time()}'
    hash_result = hashlib.sha256(payload.encode('Utf-8'))
    return hash_result.hexdigest()[:TOKEN_LENGTH].upper()


def normalize_token(text: str) -> str:
    """去除消息中的指令前缀与空白，返回规范化令牌文本。"""
    token = text.strip()
    for prefix in config.command_start:
        token = token.removeprefix(prefix)
    return token.upper()


def refresh_token() -> str:
    """刷新令牌：重新计算并覆盖当前令牌（即用即刷），返回新令牌。"""
    Globals.auth_token = generate_token()
    logger.info(f'Auth token: <red><b><u>{Globals.auth_token}</u></b></red>, copy and send it in message/command groups to complete setup.')
    return Globals.auth_token


def token_rule(message: UniMsg) -> bool:
    """匹配携带有效认证令牌的消息（非消息事件由依赖跳过）。"""
    plain_text = message.extract_plain_text()
    return bool(plain_text) and (normalize_token(plain_text) == Globals.auth_token)


# 优先级 0 并阻断：令牌消息不落入其他响应器（避免被同步到游戏），普通消息规则不命中不受影响
token_watcher = on_message(rule=Rule(token_rule), priority=0, block=True)


@token_watcher.handle()
async def handle_auth_token(session: Uninfo, message: UniMsg) -> None:
    """校验消息中的认证令牌，通过后立即刷新令牌并授权当前群与发送者。"""
    refresh_token()
    results = []
    if group_info := get_group_info(session):
        results.append(add_group(group_info))
    results.append(add_superuser(session))
    results_text = '；\n  '.join(results)
    await token_watcher.finish(f'认证成功：\n  {results_text}')


def get_group_info(session: Uninfo) -> str | None:
    """获取会话的场景群信息，非群聊场景返回 None。"""
    if session.scene.type not in _group_scenes or not session.scene.id:
        return None
    return f'{SupportScope(session.scope).name}:{session.scene.id}'


def add_group(group_info: str) -> str:
    """将群加入指令群与消息群（写回 Config.toml 并热更新内存）。"""
    added = []
    for field_name in ('command_groups', 'message_groups'):
        current = list(getattr(config, field_name))
        if group_info in current:
            continue
        updated = current + [group_info]
        try:
            config_manager.update_config({field_name: updated})
        except Exception as error:
            logger.warning(f'Failed to write Config.toml: {error}')
            continue
        setattr(config, field_name, updated)
        added.append(field_name)
    if not added:
        return '本群已在授权列表中'
    return f'已将本群加入 {"、".join(added)}'


def add_superuser(session: Uninfo) -> str:
    """将发送者加入超级用户列表（写回 .env 并热更新内存）。"""
    user_id = str(session.user.id)
    current = list(config.superusers)
    if user_id in current:
        return '你已是超级用户'
    updated = current + [user_id]
    try:
        config_manager.update_env({'SUPERUSERS': updated})
    except Exception as error:
        logger.warning(f'Failed to write .env: {error}')
        return '超级用户写入失败'
    config.superusers = updated
    return '已将你设为超级用户'
