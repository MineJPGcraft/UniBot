"""
配置表单 Schema。

定义两组数据：
- `CONFIG_SCHEMA` / `CONFIG_GROUPS`：`Config.toml` 字段，供 `/api/config/schema` 渲染。
- `ENV_SCHEMA` / `ENV_GROUPS`：`.env` 字段，供 `/api/config/env` 渲染。
"""

from Scripts.Constants import QQ_INTENT_FIELDS

from .Adapters import PLATFORM_OPTIONS

# ===== Config.toml 字段定义 =====

CONFIG_SCHEMA = [
    {
        'key': 'admin_superusers',
        'label': '管理员视为超级用户',
        'type': 'boolean',
        'default': True,
        'description': '是否将所有管理员视为超级用户',
    },
    {
        'key': 'qq_bound_max_number',
        'label': 'QQ 绑定数量上限',
        'type': 'number',
        'default': 1,
        'description': '每名玩家最多可绑定的 QQ 号数量，设置为 0 表示不限制',
    },
    {
        'key': 'command_groups',
        'label': '指令群',
        'type': 'platform_list',
        'default': [],
        'options': PLATFORM_OPTIONS,
        'description': '机器人只响应这些平台群组内发送的指令',
    },
    {
        'key': 'message_groups',
        'label': '消息群',
        'type': 'platform_list',
        'default': [],
        'options': PLATFORM_OPTIONS,
        'description': '接收游戏消息，并可向游戏内同步群消息的群',
    },
    {
        'key': 'command_minecraft_whitelist',
        'label': '指令白名单',
        'type': 'list',
        'default': [],
        'description': 'Command 指令只允许执行以列表内容开头的 Minecraft 指令；使用时请留空黑名单',
    },
    {
        'key': 'command_minecraft_blacklist',
        'label': '指令黑名单',
        'type': 'list',
        'default': [],
        'description': 'Command 指令禁止执行以列表内容开头的 Minecraft 指令',
    },
    {
        'key': 'broadcast_server',
        'label': '播报服务器状态',
        'type': 'boolean',
        'default': True,
        'description': '是否向其他服务器和消息群播报服务器开启或关闭',
    },
    {
        'key': 'broadcast_player',
        'label': '播报玩家进出',
        'type': 'boolean',
        'default': True,
        'description': '是否播报玩家进入或离开服务器',
    },
    {
        'key': 'sync_all_qq_message',
        'label': '同步全部群消息',
        'type': 'boolean',
        'default': True,
        'description': '是否将消息群内的所有消息转发到服务器；关闭后可使用 send 指令发送消息',
    },
    {
        'key': 'sync_all_game_message',
        'label': '同步全部游戏消息',
        'type': 'boolean',
        'default': False,
        'description': '是否将服务器内发送的所有消息转发到消息群',
    },
    {
        'key': 'sync_message_between_servers',
        'label': '服务器间同步消息',
        'type': 'boolean',
        'default': False,
        'description': '是否将服务器内的消息转发到其他服务器',
    },
    {
        'key': 'sync_sensitive_words',
        'label': '同步敏感词',
        'type': 'list',
        'default': [],
        'description': '包含列表中任意敏感词的消息不会同步到消息群，而会提示消息违禁',
    },
    {
        'key': 'sync_color_source',
        'label': '消息来源颜色',
        'type': 'string',
        'default': 'gray',
        'description': '群消息和跨服消息转发时，消息来源部分使用的 Minecraft 颜色',
    },
    {
        'key': 'sync_color_player',
        'label': '玩家名称颜色',
        'type': 'string',
        'default': 'gray',
        'description': '群消息和跨服消息转发时，玩家名称部分使用的 Minecraft 颜色',
    },
    {
        'key': 'sync_color_message',
        'label': '消息内容颜色',
        'type': 'string',
        'default': 'gray',
        'description': '群消息和跨服消息转发时，消息内容部分使用的 Minecraft 颜色',
    },
    {
        'key': 'bot_prefix',
        'label': '假人前缀',
        'type': 'string',
        'default': '',
        'description': 'list 指令分类和进服广播判定使用的假人名称前缀；无需分类时留空',
    },
    {
        'key': 'list_compatible_mode',
        'label': '玩家列表兼容模式',
        'type': 'boolean',
        'default': False,
        'description': '通过监听玩家进入和离开更新玩家列表，适用于无法直接获取列表的服务器，但数据可能不准确',
    },
    {
        'key': 'whitelist_command',
        'label': '白名单指令名称',
        'type': 'string',
        'default': 'whitelist',
        'description': '服务器用于管理白名单的 Minecraft 指令名称',
    },
    {
        'key': 'image.mode',
        'label': '启用图片模式',
        'type': 'boolean',
        'default': False,
        'description': '将机器人发送的消息渲染为图片；需要额外安装图片依赖，且响应速度会变慢',
    },
    {
        'key': 'webui.enabled',
        'label': '启用 WebUI',
        'type': 'boolean',
        'default': False,
        'description': '是否启用 WebUI 管理面板，并在机器人端口挂载 Web API 与 WebSocket',
    },
]

CONFIG_GROUPS = [
    {'name': '基础与权限', 'keys': ['admin_superusers', 'qq_bound_max_number']},
    {'name': '群组', 'keys': ['command_groups', 'message_groups']},
    {'name': 'Minecraft 指令', 'keys': ['command_minecraft_whitelist', 'command_minecraft_blacklist']},
    {'name': '消息播报', 'keys': ['broadcast_server', 'broadcast_player']},
    {
        'name': '消息同步',
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
    {'name': '玩家列表', 'keys': ['bot_prefix', 'list_compatible_mode', 'whitelist_command']},
    {
        'name': '图片渲染',
        'keys': ['image.mode'],
        # 门控开关：仅当该 key 为 true 时组内字段可编辑；前端据此渲染锁定遮罩
        # 'gated_by': 'image.mode',
    },
    {'name': 'WebUI', 'keys': ['webui.enabled']},
]

# ===== .env 环境变量字段定义 =====

# QQ 官方机器人 Intent 订阅清单：单一来源在 Scripts/Constants.py（扫码登录默认值共用）

ENV_SCHEMA = [
    {'key': 'PORT', 'label': '监听端口', 'type': 'number', 'default': 8000, 'description': 'NoneBot 监听的端口'},
    {
        'key': 'HOST',
        'label': '监听地址',
        'type': 'string',
        'default': '127.0.0.1',
        'description': 'NoneBot 监听的 IP / 主机名，公网连接请改为 0.0.0.0',
    },
    {
        'key': 'SUPERUSERS',
        'label': '超级用户',
        'type': 'list',
        'default': [],
        'description': '拥有管理权限的用户标识（如 QQ 号）',
    },
    {
        'key': 'COMMAND_SEP',
        'label': '命令分隔符',
        'type': 'list',
        'default': [' '],
        'description': 'NoneBot 命令分隔字符',
    },
    {
        'key': 'COMMAND_START',
        'label': '命令起始符',
        'type': 'list',
        'default': ['.'],
        'description': 'NoneBot 命令起始字符',
    },
    {'key': 'LOG_LEVEL', 'label': '日志等级', 'type': 'string', 'default': 'INFO', 'description': '日志输出等级'},
    {
        'key': 'DRIVER',
        'label': 'NoneBot 驱动',
        'type': 'string',
        'default': '~fastapi',
        'description': 'NoneBot 运行所需的驱动组合，安装/卸载适配器时会自动维护',
    },
    # ===== OneBot V11 =====
    {
        'key': 'ONEBOT_ACCESS_TOKEN',
        'label': 'OneBot AccessToken',
        'type': 'secret',
        'default': '',
        'description': 'OneBot V11 平台的 AccessToken，由 OneBot 服务端设置；未启用请留空',
    },
    # ===== QQ =====
    {
        'key': 'QQ_BOTS',
        'label': 'QQ 机器人',
        'type': 'json',
        'default': [],
        'description': 'QQ 开放平台官方机器人列表；每个机器人需配置 AppID、Secret，并按需订阅事件（Intent）。使用 WebHook 连接时在开放平台配置回调地址。',
        'form': {
            'kind': 'array',
            'item_title': '机器人',
            # 扫码快速绑定：前端据此在机器人卡片上渲染「扫码」按钮，扫码成功回填 id / secret
            'qr_connect': {
                'id_key': 'id',
                'secret_key': 'secret',
                'source': 'qq_official',
                'hint': '使用手机 QQ 扫码，自动填充 AppID 与 Secret',
            },
            'fields': [
                {
                    'key': 'id',
                    'label': 'AppID',
                    'type': 'string',
                    'required': True,
                    'description': 'QQ 开放平台应用的 AppID',
                },
                {
                    'key': 'secret',
                    'label': 'Secret',
                    'type': 'secret',
                    'required': True,
                    'description': 'QQ 开放平台应用的 Secret，用于消息签名与事件验签',
                },
                {
                    'key': 'token',
                    'label': 'Token',
                    'type': 'secret',
                    'description': 'QQ 开放平台应用的机器人 Token，仅 WebSocket 连接需要',
                },
                {
                    'key': 'intent',
                    'label': '事件订阅（Intent）',
                    'type': 'object',
                    'kind': 'booleans',
                    'fields': QQ_INTENT_FIELDS,
                    'description': '仅 WebSocket 连接生效，需按机器人类型订阅所需事件',
                },
                {
                    'key': 'use_websocket',
                    'label': '使用 WebSocket 连接',
                    'type': 'boolean',
                    'default': True,
                    'description': '关闭后改用 WebHook 连接，需在开放平台配置回调地址',
                },
            ],
        },
    },
    {
        'key': 'QQ_IS_SANDBOX',
        'label': 'QQ 沙盒模式',
        'type': 'boolean',
        'default': False,
        'description': '是否启用 QQ 沙盒模式，默认关闭',
    },
    # ===== Telegram =====
    {
        'key': 'TELEGRAM_BOTS',
        'label': 'Telegram 机器人',
        'type': 'json',
        'default': [],
        'description': 'Telegram 机器人列表；Token 向 @BotFather 申请（必填）。默认使用 Long Polling 长轮询，开启 Webhook 需配合公网 HTTPS 地址。',
        'form': {
            'kind': 'array',
            'item_title': '机器人',
            'item_placeholder': '名称',
            'fields': [
                {
                    'key': 'token',
                    'label': '机器人 Token',
                    'type': 'secret',
                    'required': True,
                    'description': '向 @BotFather 申请，格式如 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                },
                {
                    'key': 'is_webhook',
                    'label': '使用 Webhook 模式',
                    'type': 'boolean',
                    'default': False,
                    'description': '关闭则使用 Long Polling 长轮询（推荐）',
                },
            ],
        },
    },
    {
        'key': 'TELEGRAM_WEBHOOK_URL',
        'label': 'Telegram Webhook 地址',
        'type': 'string',
        'default': '',
        'description': 'Webhook 模式下的公网 HTTPS 地址，例如 https://yourdomain.com；Long polling 模式留空',
    },
    {
        'key': 'TELEGRAM_PROXY',
        'label': 'Telegram 代理',
        'type': 'string',
        'default': '',
        'description': '访问 Telegram API 的代理地址，例如 http://127.0.0.1:10809；Socks 协议需安装 httpx[socks]',
    },
    # ===== Discord =====
    {
        'key': 'DISCORD_BOTS',
        'label': 'Discord 机器人',
        'type': 'json',
        'default': [],
        'description': 'Discord 机器人列表；每个机器人需 Bot Token，并按需订阅事件（Intent）。message_content 为特权 Intent，需在开发者平台开启。',
        'form': {
            'kind': 'array',
            'item_title': '机器人',
            'fields': [
                {
                    'key': 'token',
                    'label': 'Bot Token',
                    'type': 'secret',
                    'required': True,
                    'description': 'Discord Developer Portal 中应用的 Bot Token',
                },
                {
                    'key': 'intent',
                    'label': '事件订阅（Intent）',
                    'type': 'object',
                    'kind': 'booleans',
                    'fields': [
                        {'key': 'guilds', 'label': '服务器事件', 'type': 'boolean', 'default': True},
                        {
                            'key': 'guild_messages',
                            'label': '服务器消息事件',
                            'type': 'boolean',
                            'default': True,
                        },
                        {
                            'key': 'direct_messages',
                            'label': '私信事件',
                            'type': 'boolean',
                            'default': True,
                        },
                        {
                            'key': 'message_content',
                            'label': '消息内容（特权）',
                            'type': 'boolean',
                            'default': False,
                            'description': '特权 Intent，需在开发者平台开启 Message Content Intent',
                        },
                        {
                            'key': 'guild_members',
                            'label': '服务器成员事件',
                            'type': 'boolean',
                            'default': True,
                        },
                    ],
                },
                {
                    'key': 'application_commands',
                    'label': '斜杠命令注册范围',
                    'type': 'object',
                    'kind': 'map',
                    'value_type': 'list',
                    'description': '命令名 → 服务器 ID 列表；{"*": ["*"]} 表示全部注册为全局命令',
                },
            ],
        },
    },
    {
        'key': 'DISCORD_API_VERSION',
        'label': 'Discord API 版本',
        'type': 'number',
        'default': 10,
        'description': 'Discord API 版本号，默认 10',
    },
    {
        'key': 'DISCORD_API_TIMEOUT',
        'label': 'Discord API 超时',
        'type': 'number',
        'default': 30,
        'description': 'Discord API 请求超时时间（秒），默认 30',
    },
    {
        'key': 'DISCORD_COMPRESS',
        'label': 'Discord 数据压缩',
        'type': 'boolean',
        'default': False,
        'description': '是否启用网关数据压缩，默认关闭',
    },
    {
        'key': 'DISCORD_HANDLE_SELF_MESSAGE',
        'label': 'Discord 处理自身消息',
        'type': 'boolean',
        'default': False,
        'description': '是否处理自己发送的消息，默认关闭',
    },
    {
        'key': 'DISCORD_PROXY',
        'label': 'Discord 代理',
        'type': 'string',
        'default': '',
        'description': '访问 Discord API 的代理地址，例如 http://127.0.0.1:6666；不使用请留空',
    },
    # ===== DoDo =====
    {
        'key': 'DODO_BOTS',
        'label': 'DoDo 机器人',
        'type': 'json',
        'default': [],
        'description': 'DoDo 开放平台机器人列表（仅支持 WebSocket 连接）；在开放平台创建机器人获取 client_id 与 token。',
        'form': {
            'kind': 'array',
            'item_title': '机器人',
            'fields': [
                {
                    'key': 'client_id',
                    'label': 'Client ID',
                    'type': 'string',
                    'required': True,
                    'description': 'DoDo 开放平台机器的 Client ID',
                },
                {
                    'key': 'token',
                    'label': 'Token',
                    'type': 'secret',
                    'required': True,
                    'description': 'DoDo 开放平台机器的 Token',
                },
            ],
        },
    },
    # ===== KOOK =====
    {
        'key': 'KAIHEILA_BOTS',
        'label': 'KOOK 机器人',
        'type': 'json',
        'default': [],
        'description': 'KOOK（开黑啦）机器人列表；Token 在开发者平台获取（必填）。',
        'form': {
            'kind': 'array',
            'item_title': '机器人',
            'fields': [
                {
                    'key': 'token',
                    'label': '机器人 Token',
                    'type': 'secret',
                    'required': True,
                    'description': 'KOOK 开发者平台 → 应用 → 机器人连接模式 获取的 Token',
                },
            ],
        },
    },
    # ===== Satori =====
    {
        'key': 'SATORI_CLIENTS',
        'label': 'Satori 服务',
        'type': 'json',
        'default': [],
        'description': 'Satori 协议客户端列表，用于连接 Chronocat、LLBot、Koishi 等 Satori 服务端。',
        'form': {
            'kind': 'array',
            'item_title': '连接',
            'item_placeholder': '名称',
            'fields': [
                {
                    'key': 'host',
                    'label': '连接地址',
                    'type': 'string',
                    'default': 'localhost',
                    'description': 'Satori 服务端监听地址，如 localhost',
                },
                {
                    'key': 'port',
                    'label': '端口',
                    'type': 'number',
                    'default': 5500,
                    'description': 'Satori 服务端监听端口，Chronocat 默认为 5500',
                },
                {
                    'key': 'path',
                    'label': '路径',
                    'type': 'string',
                    'default': '',
                    'description': '服务端自定义监听路径，如 /satori，默认为空',
                },
                {
                    'key': 'token',
                    'label': 'Token',
                    'type': 'secret',
                    'default': '',
                    'description': '服务端要求的验证 Token（如对接 Chronocat 需要）',
                },
                {
                    'key': 'timeout',
                    'label': '超时时间',
                    'type': 'number',
                    'default': 30,
                    'description': '连接超时时间（秒）',
                },
                {
                    'key': 'secure',
                    'label': '使用 TLS',
                    'type': 'boolean',
                    'default': False,
                    'description': '是否使用 TLS / wss 加密连接',
                },
            ],
        },
    },
    # ===== Minecraft =====
    {
        'key': 'MINECRAFT_WS_URLS',
        'label': 'Minecraft WS 地址',
        'type': 'json',
        'default': {},
        'description': 'Minecraft WebSocket 连接地址：服务器名称 → 地址列表（支持一服多地址）',
        'form': {
            'kind': 'map',
            'key_label': '服务器名称',
            'value_type': 'list',
            'value_placeholder': 'ws://地址:端口/路径',
        },
    },
    {
        'key': 'MINECRAFT_ACCESS_TOKEN',
        'label': 'Minecraft 令牌',
        'type': 'secret',
        'default': '',
        'description': 'Minecraft WebSocket 连接令牌，未设置请留空',
    },
]

ENV_GROUPS = [
    {
        'name': '框架',
        'keys': ['PORT', 'HOST', 'SUPERUSERS', 'COMMAND_SEP', 'COMMAND_START', 'LOG_LEVEL', 'DRIVER'],
    },
    {
        'name': 'OneBot V11',
        'keys': ['ONEBOT_ACCESS_TOKEN'],
    },
    {
        'name': 'QQ',
        'keys': ['QQ_BOTS', 'QQ_IS_SANDBOX'],
    },
    {
        'name': 'Telegram',
        'keys': ['TELEGRAM_BOTS', 'TELEGRAM_WEBHOOK_URL', 'TELEGRAM_PROXY'],
    },
    {
        'name': 'Discord',
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
        'name': 'DoDo',
        'keys': ['DODO_BOTS'],
    },
    {
        'name': 'KOOK',
        'keys': ['KAIHEILA_BOTS'],
    },
    {
        'name': 'Satori',
        'keys': ['SATORI_CLIENTS'],
    },
    {
        'name': 'Minecraft',
        'keys': ['MINECRAFT_WS_URLS', 'MINECRAFT_ACCESS_TOKEN'],
    },
]
