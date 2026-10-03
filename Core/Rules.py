from nonebot.rule import Rule
from nonebot_plugin_uninfo import SupportScope, Uninfo

from .Config import config


def _in_groups(session: Uninfo, groups: list[str]) -> bool:
    scope = SupportScope(session.scope)
    group_info = f'{scope.name}:{session.scene.id}'
    return group_info in groups


def is_message_group(session: Uninfo):
    return _in_groups(session, config.message_groups)


def is_command_group(session: Uninfo):
    return _in_groups(session, config.command_groups)


message_group_rule = Rule(is_message_group)
command_group_rule = Rule(is_command_group)
