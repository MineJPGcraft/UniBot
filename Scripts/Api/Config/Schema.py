"""
配置表单 Schema。

定义两组构建函数（每次调用返回全新结构，供路由按当前请求语言动态生成）：
- `build_config_schema()` / `build_config_groups()`：`Config.toml` 字段，供 `/api/config/schema` 渲染。
- `build_env_schema()` / `build_env_groups()`：`.env` 字段，供 `/api/config/env` 渲染。
"""

from Scripts.Api.Locale import text
from Scripts.Constants import QQ_INTENT_FIELDS

from .Adapters import PLATFORM_OPTIONS


def _platform_options() -> list[dict]:
    """构建注入请求语言译名的平台选项列表。"""
    return [
        {'value': option['value'], 'label': text(f'adapters.platform.{option["value"]}_label')}
        for option in PLATFORM_OPTIONS
    ]


# ===== Config.toml 字段定义 =====


def build_config_schema() -> list[dict]:
    """构建 Config.toml 字段 Schema（每次调用返回全新结构）。"""
    return [
        {
            'key': 'admin_superusers',
            'label': text('schema.config.admin_superusers_label'),
            'type': 'boolean',
            'default': True,
            'description': text('schema.config.admin_superusers_description'),
        },
        {
            'key': 'qq_bound_max_number',
            'label': text('schema.config.qq_bound_max_number_label'),
            'type': 'number',
            'default': 1,
            'description': text('schema.config.qq_bound_max_number_description'),
        },
        {
            'key': 'command_groups',
            'label': text('schema.config.command_groups_label'),
            'type': 'platform_list',
            'default': [],
            'options': _platform_options(),
            'description': text('schema.config.command_groups_description'),
        },
        {
            'key': 'message_groups',
            'label': text('schema.config.message_groups_label'),
            'type': 'platform_list',
            'default': [],
            'options': _platform_options(),
            'description': text('schema.config.message_groups_description'),
        },
        {
            'key': 'command_minecraft_whitelist',
            'label': text('schema.config.command_minecraft_whitelist_label'),
            'type': 'list',
            'default': [],
            'description': text('schema.config.command_minecraft_whitelist_description'),
        },
        {
            'key': 'command_minecraft_blacklist',
            'label': text('schema.config.command_minecraft_blacklist_label'),
            'type': 'list',
            'default': [],
            'description': text('schema.config.command_minecraft_blacklist_description'),
        },
        {
            'key': 'broadcast_server',
            'label': text('schema.config.broadcast_server_label'),
            'type': 'boolean',
            'default': True,
            'description': text('schema.config.broadcast_server_description'),
        },
        {
            'key': 'broadcast_player',
            'label': text('schema.config.broadcast_player_label'),
            'type': 'boolean',
            'default': True,
            'description': text('schema.config.broadcast_player_description'),
        },
        {
            'key': 'broadcast_update',
            'label': text('schema.config.broadcast_update_label'),
            'type': 'boolean',
            'default': True,
            'description': text('schema.config.broadcast_update_description'),
        },
        {
            'key': 'sync_command_panels',
            'label': text('schema.config.sync_command_panels_label'),
            'type': 'boolean',
            'default': True,
            'description': text('schema.config.sync_command_panels_description'),
        },
        {
            'key': 'sync_all_qq_message',
            'label': text('schema.config.sync_all_qq_message_label'),
            'type': 'boolean',
            'default': True,
            'description': text('schema.config.sync_all_qq_message_description'),
        },
        {
            'key': 'sync_all_game_message',
            'label': text('schema.config.sync_all_game_message_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.config.sync_all_game_message_description'),
        },
        {
            'key': 'sync_message_between_servers',
            'label': text('schema.config.sync_message_between_servers_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.config.sync_message_between_servers_description'),
        },
        {
            'key': 'sync_sensitive_words',
            'label': text('schema.config.sync_sensitive_words_label'),
            'type': 'list',
            'default': [],
            'description': text('schema.config.sync_sensitive_words_description'),
        },
        {
            'key': 'sync_color_source',
            'label': text('schema.config.sync_color_source_label'),
            'type': 'string',
            'default': 'gray',
            'description': text('schema.config.sync_color_source_description'),
        },
        {
            'key': 'sync_color_player',
            'label': text('schema.config.sync_color_player_label'),
            'type': 'string',
            'default': 'gray',
            'description': text('schema.config.sync_color_player_description'),
        },
        {
            'key': 'sync_color_message',
            'label': text('schema.config.sync_color_message_label'),
            'type': 'string',
            'default': 'gray',
            'description': text('schema.config.sync_color_message_description'),
        },
        {
            'key': 'bot_prefix',
            'label': text('schema.config.bot_prefix_label'),
            'type': 'string',
            'default': '',
            'description': text('schema.config.bot_prefix_description'),
        },
        {
            'key': 'list_compatible_mode',
            'label': text('schema.config.list_compatible_mode_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.config.list_compatible_mode_description'),
        },
        {
            'key': 'whitelist_command',
            'label': text('schema.config.whitelist_command_label'),
            'type': 'string',
            'default': 'whitelist',
            'description': text('schema.config.whitelist_command_description'),
        },
        {
            'key': 'image.mode',
            'label': text('schema.config.image__mode_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.config.image__mode_description'),
        },
        {
            'key': 'webui.enabled',
            'label': text('schema.config.webui__enabled_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.config.webui__enabled_description'),
        },
    ]


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


def build_env_schema() -> list[dict]:
    """构建 .env 字段 Schema（每次调用返回全新结构）。"""
    return [
        {
            'key': 'PORT',
            'label': text('schema.env.PORT_label'),
            'type': 'number',
            'default': 8000,
            'description': text('schema.env.PORT_description'),
        },
        {
            'key': 'HOST',
            'label': text('schema.env.HOST_label'),
            'type': 'string',
            'default': '127.0.0.1',
            'description': text('schema.env.HOST_description'),
        },
        {
            'key': 'SUPERUSERS',
            'label': text('schema.env.SUPERUSERS_label'),
            'type': 'list',
            'default': [],
            'description': text('schema.env.SUPERUSERS_description'),
        },
        {
            'key': 'COMMAND_SEP',
            'label': text('schema.env.COMMAND_SEP_label'),
            'type': 'list',
            'default': [' '],
            'description': text('schema.env.COMMAND_SEP_description'),
        },
        {
            'key': 'COMMAND_START',
            'label': text('schema.env.COMMAND_START_label'),
            'type': 'list',
            'default': ['.'],
            'description': text('schema.env.COMMAND_START_description'),
        },
        {
            'key': 'LOG_LEVEL',
            'label': text('schema.env.LOG_LEVEL_label'),
            'type': 'string',
            'default': 'INFO',
            'description': text('schema.env.LOG_LEVEL_description'),
        },
        {
            'key': 'DRIVER',
            'label': text('schema.env.DRIVER_label'),
            'type': 'string',
            'default': '~fastapi',
            'description': text('schema.env.DRIVER_description'),
        },
        # ===== OneBot V11 =====
        {
            'key': 'ONEBOT_ACCESS_TOKEN',
            'label': text('schema.env.ONEBOT_ACCESS_TOKEN_label'),
            'type': 'secret',
            'default': '',
            'description': text('schema.env.ONEBOT_ACCESS_TOKEN_description'),
        },
        # ===== QQ =====
        {
            'key': 'QQ_BOTS',
            'label': text('schema.env.QQ_BOTS_label'),
            'type': 'json',
            'default': [],
            'description': text('schema.env.QQ_BOTS_description'),
            'form': {
                'kind': 'array',
                'item_title': text('schema.env.QQ_BOTS_form_item_title'),
                # 扫码快速绑定：前端据此在机器人卡片上渲染「扫码」按钮，扫码成功回填 id / secret
                'qr_connect': {
                    'id_key': 'id',
                    'secret_key': 'secret',
                    'source': 'qq_official',
                    'hint': text('schema.env.QQ_BOTS_form_qr_hint'),
                },
                'fields': [
                    {
                        'key': 'id',
                        'label': text('schema.env.QQ_BOTS_field_id_label'),
                        'type': 'string',
                        'required': True,
                        'description': text('schema.env.QQ_BOTS_field_id_description'),
                    },
                    {
                        'key': 'secret',
                        'label': text('schema.env.QQ_BOTS_field_secret_label'),
                        'type': 'secret',
                        'required': True,
                        'description': text('schema.env.QQ_BOTS_field_secret_description'),
                    },
                    {
                        'key': 'token',
                        'label': text('schema.env.QQ_BOTS_field_token_label'),
                        'type': 'secret',
                        'description': text('schema.env.QQ_BOTS_field_token_description'),
                    },
                    {
                        'key': 'intent',
                        'label': text('schema.env.QQ_BOTS_field_intent_label'),
                        'type': 'object',
                        'kind': 'booleans',
                        'fields': [
                            {
                                'key': intent_field['key'],
                                'label': text(f'schema.intent.{intent_field["key"]}'),
                                'type': intent_field['type'],
                                'default': intent_field['default'],
                            }
                            for intent_field in QQ_INTENT_FIELDS
                        ],
                        'description': text('schema.env.QQ_BOTS_field_intent_description'),
                    },
                    {
                        'key': 'use_websocket',
                        'label': text('schema.env.QQ_BOTS_field_use_websocket_label'),
                        'type': 'boolean',
                        'default': True,
                        'description': text('schema.env.QQ_BOTS_field_use_websocket_description'),
                    },
                ],
            },
        },
        {
            'key': 'QQ_IS_SANDBOX',
            'label': text('schema.env.QQ_IS_SANDBOX_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.env.QQ_IS_SANDBOX_description'),
        },
        # ===== Telegram =====
        {
            'key': 'TELEGRAM_BOTS',
            'label': text('schema.env.TELEGRAM_BOTS_label'),
            'type': 'json',
            'default': [],
            'description': text('schema.env.TELEGRAM_BOTS_description'),
            'form': {
                'kind': 'array',
                'item_title': text('schema.env.TELEGRAM_BOTS_form_item_title'),
                'item_placeholder': text('schema.env.TELEGRAM_BOTS_form_item_placeholder'),
                'fields': [
                    {
                        'key': 'token',
                        'label': text('schema.env.TELEGRAM_BOTS_field_token_label'),
                        'type': 'secret',
                        'required': True,
                        'description': text('schema.env.TELEGRAM_BOTS_field_token_description'),
                    },
                    {
                        'key': 'is_webhook',
                        'label': text('schema.env.TELEGRAM_BOTS_field_is_webhook_label'),
                        'type': 'boolean',
                        'default': False,
                        'description': text('schema.env.TELEGRAM_BOTS_field_is_webhook_description'),
                    },
                ],
            },
        },
        {
            'key': 'TELEGRAM_WEBHOOK_URL',
            'label': text('schema.env.TELEGRAM_WEBHOOK_URL_label'),
            'type': 'string',
            'default': '',
            'description': text('schema.env.TELEGRAM_WEBHOOK_URL_description'),
        },
        {
            'key': 'TELEGRAM_PROXY',
            'label': text('schema.env.TELEGRAM_PROXY_label'),
            'type': 'string',
            'default': '',
            'description': text('schema.env.TELEGRAM_PROXY_description'),
        },
        # ===== Discord =====
        {
            'key': 'DISCORD_BOTS',
            'label': text('schema.env.DISCORD_BOTS_label'),
            'type': 'json',
            'default': [],
            'description': text('schema.env.DISCORD_BOTS_description'),
            'form': {
                'kind': 'array',
                'item_title': text('schema.env.DISCORD_BOTS_form_item_title'),
                'fields': [
                    {
                        'key': 'token',
                        'label': text('schema.env.DISCORD_BOTS_field_token_label'),
                        'type': 'secret',
                        'required': True,
                        'description': text('schema.env.DISCORD_BOTS_field_token_description'),
                    },
                    {
                        'key': 'intent',
                        'label': text('schema.env.DISCORD_BOTS_field_intent_label'),
                        'type': 'object',
                        'kind': 'booleans',
                        'fields': [
                            {
                                'key': 'guilds',
                                'label': text('schema.env.DISCORD_BOTS_field_guilds_label'),
                                'type': 'boolean',
                                'default': True,
                            },
                            {
                                'key': 'guild_messages',
                                'label': text('schema.env.DISCORD_BOTS_field_guild_messages_label'),
                                'type': 'boolean',
                                'default': True,
                            },
                            {
                                'key': 'direct_messages',
                                'label': text('schema.env.DISCORD_BOTS_field_direct_messages_label'),
                                'type': 'boolean',
                                'default': True,
                            },
                            {
                                'key': 'message_content',
                                'label': text('schema.env.DISCORD_BOTS_field_message_content_label'),
                                'type': 'boolean',
                                'default': False,
                                'description': text('schema.env.DISCORD_BOTS_field_message_content_description'),
                            },
                            {
                                'key': 'guild_members',
                                'label': text('schema.env.DISCORD_BOTS_field_guild_members_label'),
                                'type': 'boolean',
                                'default': True,
                            },
                        ],
                    },
                    {
                        'key': 'application_commands',
                        'label': text('schema.env.DISCORD_BOTS_field_application_commands_label'),
                        'type': 'object',
                        'kind': 'map',
                        'value_type': 'list',
                        'description': text('schema.env.DISCORD_BOTS_field_application_commands_description'),
                    },
                ],
            },
        },
        {
            'key': 'DISCORD_API_VERSION',
            'label': text('schema.env.DISCORD_API_VERSION_label'),
            'type': 'number',
            'default': 10,
            'description': text('schema.env.DISCORD_API_VERSION_description'),
        },
        {
            'key': 'DISCORD_API_TIMEOUT',
            'label': text('schema.env.DISCORD_API_TIMEOUT_label'),
            'type': 'number',
            'default': 30,
            'description': text('schema.env.DISCORD_API_TIMEOUT_description'),
        },
        {
            'key': 'DISCORD_COMPRESS',
            'label': text('schema.env.DISCORD_COMPRESS_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.env.DISCORD_COMPRESS_description'),
        },
        {
            'key': 'DISCORD_HANDLE_SELF_MESSAGE',
            'label': text('schema.env.DISCORD_HANDLE_SELF_MESSAGE_label'),
            'type': 'boolean',
            'default': False,
            'description': text('schema.env.DISCORD_HANDLE_SELF_MESSAGE_description'),
        },
        {
            'key': 'DISCORD_PROXY',
            'label': text('schema.env.DISCORD_PROXY_label'),
            'type': 'string',
            'default': '',
            'description': text('schema.env.DISCORD_PROXY_description'),
        },
        # ===== DoDo =====
        {
            'key': 'DODO_BOTS',
            'label': text('schema.env.DODO_BOTS_label'),
            'type': 'json',
            'default': [],
            'description': text('schema.env.DODO_BOTS_description'),
            'form': {
                'kind': 'array',
                'item_title': text('schema.env.DODO_BOTS_form_item_title'),
                'fields': [
                    {
                        'key': 'client_id',
                        'label': text('schema.env.DODO_BOTS_field_client_id_label'),
                        'type': 'string',
                        'required': True,
                        'description': text('schema.env.DODO_BOTS_field_client_id_description'),
                    },
                    {
                        'key': 'token',
                        'label': text('schema.env.DODO_BOTS_field_token_label'),
                        'type': 'secret',
                        'required': True,
                        'description': text('schema.env.DODO_BOTS_field_token_description'),
                    },
                ],
            },
        },
        # ===== KOOK =====
        {
            'key': 'KAIHEILA_BOTS',
            'label': text('schema.env.KAIHEILA_BOTS_label'),
            'type': 'json',
            'default': [],
            'description': text('schema.env.KAIHEILA_BOTS_description'),
            'form': {
                'kind': 'array',
                'item_title': text('schema.env.KAIHEILA_BOTS_form_item_title'),
                'fields': [
                    {
                        'key': 'token',
                        'label': text('schema.env.KAIHEILA_BOTS_field_token_label'),
                        'type': 'secret',
                        'required': True,
                        'description': text('schema.env.KAIHEILA_BOTS_field_token_description'),
                    },
                ],
            },
        },
        # ===== Satori =====
        {
            'key': 'SATORI_CLIENTS',
            'label': text('schema.env.SATORI_CLIENTS_label'),
            'type': 'json',
            'default': [],
            'description': text('schema.env.SATORI_CLIENTS_description'),
            'form': {
                'kind': 'array',
                'item_title': text('schema.env.SATORI_CLIENTS_form_item_title'),
                'item_placeholder': text('schema.env.SATORI_CLIENTS_form_item_placeholder'),
                'fields': [
                    {
                        'key': 'host',
                        'label': text('schema.env.SATORI_CLIENTS_field_host_label'),
                        'type': 'string',
                        'default': 'localhost',
                        'description': text('schema.env.SATORI_CLIENTS_field_host_description'),
                    },
                    {
                        'key': 'port',
                        'label': text('schema.env.SATORI_CLIENTS_field_port_label'),
                        'type': 'number',
                        'default': 5500,
                        'description': text('schema.env.SATORI_CLIENTS_field_port_description'),
                    },
                    {
                        'key': 'path',
                        'label': text('schema.env.SATORI_CLIENTS_field_path_label'),
                        'type': 'string',
                        'default': '',
                        'description': text('schema.env.SATORI_CLIENTS_field_path_description'),
                    },
                    {
                        'key': 'token',
                        'label': text('schema.env.SATORI_CLIENTS_field_token_label'),
                        'type': 'secret',
                        'default': '',
                        'description': text('schema.env.SATORI_CLIENTS_field_token_description'),
                    },
                    {
                        'key': 'timeout',
                        'label': text('schema.env.SATORI_CLIENTS_field_timeout_label'),
                        'type': 'number',
                        'default': 30,
                        'description': text('schema.env.SATORI_CLIENTS_field_timeout_description'),
                    },
                    {
                        'key': 'secure',
                        'label': text('schema.env.SATORI_CLIENTS_field_secure_label'),
                        'type': 'boolean',
                        'default': False,
                        'description': text('schema.env.SATORI_CLIENTS_field_secure_description'),
                    },
                ],
            },
        },
        # ===== Minecraft =====
        {
            'key': 'MINECRAFT_WS_URLS',
            'label': text('schema.env.MINECRAFT_WS_URLS_label'),
            'type': 'json',
            'default': {},
            'description': text('schema.env.MINECRAFT_WS_URLS_description'),
            'form': {
                'kind': 'map',
                'key_label': text('schema.env.MINECRAFT_WS_URLS_form_key_label'),
                'value_type': 'list',
                'value_placeholder': text('schema.env.MINECRAFT_WS_URLS_form_value_placeholder'),
            },
        },
        {
            'key': 'MINECRAFT_ACCESS_TOKEN',
            'label': text('schema.env.MINECRAFT_ACCESS_TOKEN_label'),
            'type': 'secret',
            'default': '',
            'description': text('schema.env.MINECRAFT_ACCESS_TOKEN_description'),
        },
    ]


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
