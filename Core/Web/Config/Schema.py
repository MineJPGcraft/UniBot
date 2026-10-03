"""
配置表单 Schema。

定义两组构建函数（每次调用返回全新结构，供路由按当前请求语言动态生成）：
- `build_config_schema()` / `build_config_groups()`：`Config.toml` 字段，供 `/api/config/schema` 渲染。
- `build_env_schema()` / `build_env_groups()`：`.env` 字段，供 `/api/config/env` 渲染。

输出为**标准 JSON Schema**（与扩展配置的 Pydantic `model_json_schema()` 同构），
前端因此只需一套表单渲染器。字段名即 `properties` 的键，另有以下约定：

| Schema 形态 | 前端控件 |
|-------------|----------|
| `boolean` | 开关 |
| `number` / `integer` | 数字输入框 |
| `string` | 文本框 |
| `string` + `format: 'password'` | 密码框（留空表示不修改） |
| `string` + `format: 'color'` | 颜色选择器 |
| `string` + `format: 'textarea'` | 多行文本框 |
| `string` + `enum` | 下拉选择 || `array` + `items.type: 'string'` | 字符串列表 |
| `array` + `items.format: 'platform'` | 平台列表（平台下拉 + 目标输入） |
| `array` + `items.$ref` | 对象数组（卡片列表，支持增删排序） |
| `object` + `additionalProperties` | 键值对编辑器 |
| `object` + `properties` | 布尔组（折叠面板内的一组开关） |

数组卡片与键值映射的展示文案通过 `x-item-title` / `x-item-placeholder` /
`x-key-label` / `x-value-placeholder` / `x-qr-connect` 携带（`x-` 前缀为
JSON Schema 的自定义扩展位，Pydantic 侧则用 `json_schema_extra` 等价表达）。
"""

from typing import Any

from Scripts.Api.Locale import text
from Scripts.Constants import QQ_INTENT_FIELDS

from .Adapters import PLATFORM_OPTIONS


def _platform_options() -> list[dict]:
    """构建注入请求语言译名的平台选项列表。"""
    return [
        {'value': option['value'], 'label': text(f'adapters.platform.{option["value"]}_label')}
        for option in PLATFORM_OPTIONS
    ]


def _platform_list_schema() -> dict[str, Any]:
    """平台列表字段：字符串数组 + 平台选项（前端渲染为平台下拉 + 目标输入）。"""
    return {
        'type': 'array',
        'items': {'type': 'string', 'format': 'platform'},
        'x-options': _platform_options(),
    }


# ===== Config.toml 字段定义 =====


def build_config_schema() -> dict:
    """构建 Config.toml 字段 Schema（每次调用返回全新结构）。"""
    return {
        'type': 'object',
        'properties': {
            'admin_superusers': {
                'type': 'boolean',
                'title': text('schema.config.admin_superusers_label'),
                'description': text('schema.config.admin_superusers_description'),
                'default': True,
            },
            'qq_bound_max_number': {
                'type': 'integer',
                'title': text('schema.config.qq_bound_max_number_label'),
                'description': text('schema.config.qq_bound_max_number_description'),
                'default': 1,
                'minimum': 0,
            },
            'command_groups': {
                **_platform_list_schema(),
                'title': text('schema.config.command_groups_label'),
                'description': text('schema.config.command_groups_description'),
                'default': [],
            },
            'message_groups': {
                **_platform_list_schema(),
                'title': text('schema.config.message_groups_label'),
                'description': text('schema.config.message_groups_description'),
                'default': [],
            },
            'command_minecraft_whitelist': {
                'type': 'array',
                'items': {'type': 'string'},
                'title': text('schema.config.command_minecraft_whitelist_label'),
                'description': text('schema.config.command_minecraft_whitelist_description'),
                'default': [],
            },
            'command_minecraft_blacklist': {
                'type': 'array',
                'items': {'type': 'string'},
                'title': text('schema.config.command_minecraft_blacklist_label'),
                'description': text('schema.config.command_minecraft_blacklist_description'),
                'default': [],
            },
            'broadcast_server': {
                'type': 'boolean',
                'title': text('schema.config.broadcast_server_label'),
                'description': text('schema.config.broadcast_server_description'),
                'default': True,
            },
            'broadcast_player': {
                'type': 'boolean',
                'title': text('schema.config.broadcast_player_label'),
                'description': text('schema.config.broadcast_player_description'),
                'default': True,
            },
            'broadcast_update': {
                'type': 'boolean',
                'title': text('schema.config.broadcast_update_label'),
                'description': text('schema.config.broadcast_update_description'),
                'default': True,
            },
            'sync_command_panels': {
                'type': 'boolean',
                'title': text('schema.config.sync_command_panels_label'),
                'description': text('schema.config.sync_command_panels_description'),
                'default': True,
            },
            'sync_all_qq_message': {
                'type': 'boolean',
                'title': text('schema.config.sync_all_qq_message_label'),
                'description': text('schema.config.sync_all_qq_message_description'),
                'default': True,
            },
            'sync_all_game_message': {
                'type': 'boolean',
                'title': text('schema.config.sync_all_game_message_label'),
                'description': text('schema.config.sync_all_game_message_description'),
                'default': False,
            },
            'sync_message_between_servers': {
                'type': 'boolean',
                'title': text('schema.config.sync_message_between_servers_label'),
                'description': text('schema.config.sync_message_between_servers_description'),
                'default': False,
            },
            'sync_sensitive_words': {
                'type': 'array',
                'items': {'type': 'string'},
                'title': text('schema.config.sync_sensitive_words_label'),
                'description': text('schema.config.sync_sensitive_words_description'),
                'default': [],
            },
            'sync_color_source': {
                'type': 'string',
                'title': text('schema.config.sync_color_source_label'),
                'description': text('schema.config.sync_color_source_description'),
                'default': 'gray',
            },
            'sync_color_player': {
                'type': 'string',
                'title': text('schema.config.sync_color_player_label'),
                'description': text('schema.config.sync_color_player_description'),
                'default': 'gray',
            },
            'sync_color_message': {
                'type': 'string',
                'title': text('schema.config.sync_color_message_label'),
                'description': text('schema.config.sync_color_message_description'),
                'default': 'gray',
            },
            'bot_prefix': {
                'type': 'string',
                'title': text('schema.config.bot_prefix_label'),
                'description': text('schema.config.bot_prefix_description'),
                'default': '',
            },
            'list_compatible_mode': {
                'type': 'boolean',
                'title': text('schema.config.list_compatible_mode_label'),
                'description': text('schema.config.list_compatible_mode_description'),
                'default': False,
            },
            'whitelist_command': {
                'type': 'string',
                'title': text('schema.config.whitelist_command_label'),
                'description': text('schema.config.whitelist_command_description'),
                'default': 'whitelist',
            },
            'image.mode': {
                'type': 'boolean',
                'title': text('schema.config.image__mode_label'),
                'description': text('schema.config.image__mode_description'),
                'default': False,
            },
            'webui.enabled': {
                'type': 'boolean',
                'title': text('schema.config.webui__enabled_label'),
                'description': text('schema.config.webui__enabled_description'),
                'default': False,
            },
        },
    }


def build_config_groups() -> list[dict]:
    """构建 Config.toml 分组（每次调用返回全新结构）。"""
    return [
        {
            'id': 'basic',
            'name': text('schema.config.group_basic'),
            'keys': ['admin_superusers', 'qq_bound_max_number'],
        },
        {
            'id': 'groups',
            'name': text('schema.config.group_groups'),
            'keys': ['command_groups', 'message_groups'],
        },
        {
            'id': 'mc_command',
            'name': text('schema.config.group_mc_command'),
            'keys': ['command_minecraft_whitelist', 'command_minecraft_blacklist'],
        },
        {
            'id': 'broadcast',
            'name': text('schema.config.group_broadcast'),
            'keys': ['broadcast_server', 'broadcast_player', 'broadcast_update', 'sync_command_panels'],
        },
        {
            'id': 'sync',
            'name': text('schema.config.group_sync'),
            'keys': [
                'sync_all_qq_message',
                'sync_all_game_message',
                'sync_message_between_servers',
                'sync_sensitive_words',
                'sync_color_source',
                'sync_color_player',
                'sync_color_message',
            ],
        },
        {
            'id': 'player_list',
            'name': text('schema.config.group_player_list'),
            'keys': ['bot_prefix', 'list_compatible_mode', 'whitelist_command'],
        },
        {
            'id': 'image',
            'name': text('schema.config.group_image'),
            'keys': ['image.mode'],
            # 门控开关：仅当该 key 为 true 时组内字段可编辑；前端据此渲染锁定遮罩
            # 'gated_by': 'image.mode',
        },
        {
            'id': 'webui',
            'name': text('schema.config.group_webui'),
            'keys': ['webui.enabled'],
        },
    ]


# ===== .env 环境变量字段定义 =====

# QQ 官方机器人 Intent 订阅清单：单一来源在 Scripts/Constants.py（扫码登录默认值共用）


def _intent_schema() -> dict[str, Any]:
    """布尔组：折叠面板内的一组开关。"""
    return {
        'type': 'object',
        'properties': {
            intent_field['key']: {
                'type': 'boolean',
                'title': text(f'schema.intent.{intent_field["key"]}'),
                'default': intent_field['default'],
            }
            for intent_field in QQ_INTENT_FIELDS
        },
    }


# 对象数组的元素定义（前端按 $ref 解析为卡片内字段）
_ENV_DEFINITIONS: dict[str, Any] = {
    'QQ_BOTSItem': {
        'type': 'object',
        'required': ['id', 'secret'],
        'properties': {
            'id': {
                'type': 'string',
                'title': text('schema.env.QQ_BOTS_field_id_label'),
                'description': text('schema.env.QQ_BOTS_field_id_description'),
            },
            'secret': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.QQ_BOTS_field_secret_label'),
                'description': text('schema.env.QQ_BOTS_field_secret_description'),
            },
            'token': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.QQ_BOTS_field_token_label'),
                'description': text('schema.env.QQ_BOTS_field_token_description'),
            },
            'intent': {
                **_intent_schema(),
                'title': text('schema.env.QQ_BOTS_field_intent_label'),
                'description': text('schema.env.QQ_BOTS_field_intent_description'),
            },
            'use_websocket': {
                'type': 'boolean',
                'title': text('schema.env.QQ_BOTS_field_use_websocket_label'),
                'description': text('schema.env.QQ_BOTS_field_use_websocket_description'),
                'default': True,
            },
        },
    },
    'TELEGRAM_BOTSItem': {
        'type': 'object',
        'required': ['token'],
        'properties': {
            'token': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.TELEGRAM_BOTS_field_token_label'),
                'description': text('schema.env.TELEGRAM_BOTS_field_token_description'),
            },
            'is_webhook': {
                'type': 'boolean',
                'title': text('schema.env.TELEGRAM_BOTS_field_is_webhook_label'),
                'description': text('schema.env.TELEGRAM_BOTS_field_is_webhook_description'),
                'default': False,
            },
        },
    },
    'DISCORD_BOTSItem': {
        'type': 'object',
        'required': ['token'],
        'properties': {
            'token': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.DISCORD_BOTS_field_token_label'),
                'description': text('schema.env.DISCORD_BOTS_field_token_description'),
            },
            'intent': {
                'type': 'object',
                'title': text('schema.env.DISCORD_BOTS_field_intent_label'),
                'properties': {
                    'guilds': {
                        'type': 'boolean',
                        'title': text('schema.env.DISCORD_BOTS_field_guilds_label'),
                        'default': True,
                    },
                    'guild_messages': {
                        'type': 'boolean',
                        'title': text('schema.env.DISCORD_BOTS_field_guild_messages_label'),
                        'default': True,
                    },
                    'direct_messages': {
                        'type': 'boolean',
                        'title': text('schema.env.DISCORD_BOTS_field_direct_messages_label'),
                        'default': True,
                    },
                    'message_content': {
                        'type': 'boolean',
                        'title': text('schema.env.DISCORD_BOTS_field_message_content_label'),
                        'description': text('schema.env.DISCORD_BOTS_field_message_content_description'),
                        'default': False,
                    },
                    'guild_members': {
                        'type': 'boolean',
                        'title': text('schema.env.DISCORD_BOTS_field_guild_members_label'),
                        'default': True,
                    },
                },
            },
            'application_commands': {
                'type': 'object',
                'additionalProperties': {'type': 'array', 'items': {'type': 'string'}},
                'title': text('schema.env.DISCORD_BOTS_field_application_commands_label'),
                'description': text('schema.env.DISCORD_BOTS_field_application_commands_description'),
            },
        },
    },
    'DODO_BOTSItem': {
        'type': 'object',
        'required': ['client_id', 'token'],
        'properties': {
            'client_id': {
                'type': 'string',
                'title': text('schema.env.DODO_BOTS_field_client_id_label'),
                'description': text('schema.env.DODO_BOTS_field_client_id_description'),
            },
            'token': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.DODO_BOTS_field_token_label'),
                'description': text('schema.env.DODO_BOTS_field_token_description'),
            },
        },
    },
    'KAIHEILA_BOTSItem': {
        'type': 'object',
        'required': ['token'],
        'properties': {
            'token': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.KAIHEILA_BOTS_field_token_label'),
                'description': text('schema.env.KAIHEILA_BOTS_field_token_description'),
            },
        },
    },
    'SATORI_CLIENTSItem': {
        'type': 'object',
        'properties': {
            'host': {
                'type': 'string',
                'title': text('schema.env.SATORI_CLIENTS_field_host_label'),
                'description': text('schema.env.SATORI_CLIENTS_field_host_description'),
                'default': 'localhost',
            },
            'port': {
                'type': 'integer',
                'title': text('schema.env.SATORI_CLIENTS_field_port_label'),
                'description': text('schema.env.SATORI_CLIENTS_field_port_description'),
                'default': 5500,
                'minimum': 1,
                'maximum': 65535,
            },
            'path': {
                'type': 'string',
                'title': text('schema.env.SATORI_CLIENTS_field_path_label'),
                'description': text('schema.env.SATORI_CLIENTS_field_path_description'),
                'default': '',
            },
            'token': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.SATORI_CLIENTS_field_token_label'),
                'description': text('schema.env.SATORI_CLIENTS_field_token_description'),
                'default': '',
            },
            'timeout': {
                'type': 'integer',
                'title': text('schema.env.SATORI_CLIENTS_field_timeout_label'),
                'description': text('schema.env.SATORI_CLIENTS_field_timeout_description'),
                'default': 30,
                'minimum': 1,
            },
            'secure': {
                'type': 'boolean',
                'title': text('schema.env.SATORI_CLIENTS_field_secure_label'),
                'description': text('schema.env.SATORI_CLIENTS_field_secure_description'),
                'default': False,
            },
        },
    },
}


def build_env_schema() -> dict:
    """构建 .env 字段 Schema（每次调用返回全新结构）。"""
    return {
        'type': 'object',
        'properties': {
            'PORT': {
                'type': 'integer',
                'title': text('schema.env.PORT_label'),
                'description': text('schema.env.PORT_description'),
                'default': 8000,
                'minimum': 1,
                'maximum': 65535,
            },
            'HOST': {
                'type': 'string',
                'title': text('schema.env.HOST_label'),
                'description': text('schema.env.HOST_description'),
                'default': '127.0.0.1',
            },
            'SUPERUSERS': {
                'type': 'array',
                'items': {'type': 'string'},
                'title': text('schema.env.SUPERUSERS_label'),
                'description': text('schema.env.SUPERUSERS_description'),
                'default': [],
            },
            'COMMAND_SEP': {
                'type': 'array',
                'items': {'type': 'string'},
                'title': text('schema.env.COMMAND_SEP_label'),
                'description': text('schema.env.COMMAND_SEP_description'),
                'default': [' '],
            },
            'COMMAND_START': {
                'type': 'array',
                'items': {'type': 'string'},
                'title': text('schema.env.COMMAND_START_label'),
                'description': text('schema.env.COMMAND_START_description'),
                'default': ['.'],
            },
            'LOG_LEVEL': {
                'type': 'string',
                'title': text('schema.env.LOG_LEVEL_label'),
                'description': text('schema.env.LOG_LEVEL_description'),
                'default': 'INFO',
            },
            'DRIVER': {
                'type': 'string',
                'title': text('schema.env.DRIVER_label'),
                'description': text('schema.env.DRIVER_description'),
                'default': '~fastapi',
            },
            # ===== OneBot V11 =====
            'ONEBOT_ACCESS_TOKEN': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.ONEBOT_ACCESS_TOKEN_label'),
                'description': text('schema.env.ONEBOT_ACCESS_TOKEN_description'),
                'default': '',
            },
            # ===== QQ =====
            'QQ_BOTS': {
                'type': 'array',
                'items': {'$ref': '#/$defs/QQ_BOTSItem'},
                'title': text('schema.env.QQ_BOTS_label'),
                'description': text('schema.env.QQ_BOTS_description'),
                'default': [],
                'x-item-title': text('schema.env.QQ_BOTS_form_item_title'),
                # 扫码快速绑定：前端据此在机器人卡片上渲染「扫码」按钮，扫码成功回填 id / secret
                'x-qr-connect': {
                    'id_key': 'id',
                    'secret_key': 'secret',
                    'source': 'qq_official',
                    'hint': text('schema.env.QQ_BOTS_form_qr_hint'),
                },
            },
            'QQ_IS_SANDBOX': {
                'type': 'boolean',
                'title': text('schema.env.QQ_IS_SANDBOX_label'),
                'description': text('schema.env.QQ_IS_SANDBOX_description'),
                'default': False,
            },
            # ===== Telegram =====
            'TELEGRAM_BOTS': {
                'type': 'array',
                'items': {'$ref': '#/$defs/TELEGRAM_BOTSItem'},
                'title': text('schema.env.TELEGRAM_BOTS_label'),
                'description': text('schema.env.TELEGRAM_BOTS_description'),
                'default': [],
                'x-item-title': text('schema.env.TELEGRAM_BOTS_form_item_title'),
                'x-item-placeholder': text('schema.env.TELEGRAM_BOTS_form_item_placeholder'),
            },
            'TELEGRAM_WEBHOOK_URL': {
                'type': 'string',
                'title': text('schema.env.TELEGRAM_WEBHOOK_URL_label'),
                'description': text('schema.env.TELEGRAM_WEBHOOK_URL_description'),
                'default': '',
            },
            'TELEGRAM_PROXY': {
                'type': 'string',
                'title': text('schema.env.TELEGRAM_PROXY_label'),
                'description': text('schema.env.TELEGRAM_PROXY_description'),
                'default': '',
            },
            # ===== Discord =====
            'DISCORD_BOTS': {
                'type': 'array',
                'items': {'$ref': '#/$defs/DISCORD_BOTSItem'},
                'title': text('schema.env.DISCORD_BOTS_label'),
                'description': text('schema.env.DISCORD_BOTS_description'),
                'default': [],
                'x-item-title': text('schema.env.DISCORD_BOTS_form_item_title'),
            },
            'DISCORD_API_VERSION': {
                'type': 'integer',
                'title': text('schema.env.DISCORD_API_VERSION_label'),
                'description': text('schema.env.DISCORD_API_VERSION_description'),
                'default': 10,
                'minimum': 9,
            },
            'DISCORD_API_TIMEOUT': {
                'type': 'integer',
                'title': text('schema.env.DISCORD_API_TIMEOUT_label'),
                'description': text('schema.env.DISCORD_API_TIMEOUT_description'),
                'default': 30,
                'minimum': 1,
            },
            'DISCORD_COMPRESS': {
                'type': 'boolean',
                'title': text('schema.env.DISCORD_COMPRESS_label'),
                'description': text('schema.env.DISCORD_COMPRESS_description'),
                'default': False,
            },
            'DISCORD_HANDLE_SELF_MESSAGE': {
                'type': 'boolean',
                'title': text('schema.env.DISCORD_HANDLE_SELF_MESSAGE_label'),
                'description': text('schema.env.DISCORD_HANDLE_SELF_MESSAGE_description'),
                'default': False,
            },
            'DISCORD_PROXY': {
                'type': 'string',
                'title': text('schema.env.DISCORD_PROXY_label'),
                'description': text('schema.env.DISCORD_PROXY_description'),
                'default': '',
            },
            # ===== DoDo =====
            'DODO_BOTS': {
                'type': 'array',
                'items': {'$ref': '#/$defs/DODO_BOTSItem'},
                'title': text('schema.env.DODO_BOTS_label'),
                'description': text('schema.env.DODO_BOTS_description'),
                'default': [],
                'x-item-title': text('schema.env.DODO_BOTS_form_item_title'),
            },
            # ===== KOOK =====
            'KAIHEILA_BOTS': {
                'type': 'array',
                'items': {'$ref': '#/$defs/KAIHEILA_BOTSItem'},
                'title': text('schema.env.KAIHEILA_BOTS_label'),
                'description': text('schema.env.KAIHEILA_BOTS_description'),
                'default': [],
                'x-item-title': text('schema.env.KAIHEILA_BOTS_form_item_title'),
            },
            # ===== Satori =====
            'SATORI_CLIENTS': {
                'type': 'array',
                'items': {'$ref': '#/$defs/SATORI_CLIENTSItem'},
                'title': text('schema.env.SATORI_CLIENTS_label'),
                'description': text('schema.env.SATORI_CLIENTS_description'),
                'default': [],
                'x-item-title': text('schema.env.SATORI_CLIENTS_form_item_title'),
                'x-item-placeholder': text('schema.env.SATORI_CLIENTS_form_item_placeholder'),
            },
            # ===== Minecraft =====
            'MINECRAFT_WS_URLS': {
                'type': 'object',
                'additionalProperties': {'type': 'array', 'items': {'type': 'string'}},
                'title': text('schema.env.MINECRAFT_WS_URLS_label'),
                'description': text('schema.env.MINECRAFT_WS_URLS_description'),
                'default': {},
                'x-key-label': text('schema.env.MINECRAFT_WS_URLS_form_key_label'),
                'x-value-placeholder': text('schema.env.MINECRAFT_WS_URLS_form_value_placeholder'),
            },
            'MINECRAFT_ACCESS_TOKEN': {
                'type': 'string',
                'format': 'password',
                'title': text('schema.env.MINECRAFT_ACCESS_TOKEN_label'),
                'description': text('schema.env.MINECRAFT_ACCESS_TOKEN_description'),
                'default': '',
            },
        },
        '$defs': _ENV_DEFINITIONS,
    }


def build_env_groups() -> list[dict]:
    """构建 .env 分组（每次调用返回全新结构）。"""
    return [
        {
            'id': 'framework',
            'name': text('schema.env.group_framework'),
            'keys': ['PORT', 'HOST', 'SUPERUSERS', 'COMMAND_SEP', 'COMMAND_START', 'LOG_LEVEL', 'DRIVER'],
        },
        {
            'id': 'onebot_v11',
            'name': text('schema.env.group_onebot_v11'),
            'keys': ['ONEBOT_ACCESS_TOKEN'],
        },
        {
            'id': 'qq',
            'name': text('schema.env.group_qq'),
            'keys': ['QQ_BOTS', 'QQ_IS_SANDBOX'],
        },
        {
            'id': 'telegram',
            'name': text('schema.env.group_telegram'),
            'keys': ['TELEGRAM_BOTS', 'TELEGRAM_WEBHOOK_URL', 'TELEGRAM_PROXY'],
        },
        {
            'id': 'discord',
            'name': text('schema.env.group_discord'),
            'keys': [
                'DISCORD_BOTS',
                'DISCORD_API_VERSION',
                'DISCORD_API_TIMEOUT',
                'DISCORD_COMPRESS',
                'DISCORD_HANDLE_SELF_MESSAGE',
                'DISCORD_PROXY',
            ],
        },
        {
            'id': 'dodo',
            'name': text('schema.env.group_dodo'),
            'keys': ['DODO_BOTS'],
        },
        {
            'id': 'kook',
            'name': text('schema.env.group_kook'),
            'keys': ['KAIHEILA_BOTS'],
        },
        {
            'id': 'satori',
            'name': text('schema.env.group_satori'),
            'keys': ['SATORI_CLIENTS'],
        },
        {
            'id': 'minecraft',
            'name': text('schema.env.group_minecraft'),
            'keys': ['MINECRAFT_WS_URLS', 'MINECRAFT_ACCESS_TOKEN'],
        },
    ]
