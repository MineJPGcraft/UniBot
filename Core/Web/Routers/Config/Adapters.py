"""
平台与适配器目录的内置常量。

包含 NoneBot 官方/社区适配器元数据、驱动映射，以及受保护的模块集合。
WebUI 通过 `ADAPTER_CATALOG` 渲染安装/卸载列表。
"""

# 所有可选平台（用于 WebUI 中的 platform_list 配置项）
# 与 Utils.scope_mapping 保持一致，仅包含有可读名称的平台。
PLATFORM_OPTIONS = [
    {'value': 'qq_client', 'label': 'QQ'},
    {'value': 'qq_api', 'label': '官方 QQ'},
    {'value': 'qq_guild', 'label': 'QQ 频道'},
    {'value': 'telegram', 'label': 'Telegram'},
    {'value': 'discord', 'label': 'Discord'},
    {'value': 'dodo', 'label': 'DoDo'},
    {'value': 'kook', 'label': 'Kook'},
    {'value': 'wechat', 'label': '微信'},
    {'value': 'wecom', 'label': '企业微信'},
]

# 基础驱动框架，必须始终保留
BASE_DRIVER = '~fastapi'

# 适配器额外所需驱动（HTTPClient / WebSocketClient）
ADAPTER_DRIVERS: dict[str, list[str]] = {
    'nonebot.adapters.onebot.v11': ['~httpx', '~websockets'],
    'nonebot.adapters.qq': ['~httpx', '~websockets'],
    'nonebot.adapters.telegram': ['~httpx', '~websockets'],
    'nonebot.adapters.discord': ['~httpx', '~websockets'],
    'nonebot.adapters.dodo': ['~httpx', '~websockets'],
    'nonebot.adapters.kaiheila': ['~httpx', '~websockets'],
    'nonebot.adapters.satori': ['~httpx', '~websockets'],
    'nonebot.adapters.minecraft': ['~websockets'],
}

# 适配器目录：WebUI 用于展示、安装、卸载
ADAPTER_CATALOG = [
    {
        'id': 'onebot-v11',
        'name': 'OneBot V11',
        'package': 'nonebot-adapter-onebot',
        'module_name': 'nonebot.adapters.onebot.v11',
        'author': 'yanyongyu',
        'homepage': 'https://onebot.adapters.nonebot.dev/',
        'is_official': True,
        'platforms': ['qq_client'],
        'description': '适用于 Lagrange.OneBot、NapCat、LLOneBot 等 OneBot V11 实现。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.onebot.v11'],
        'config_keys': ['ONEBOT_ACCESS_TOKEN'],
    },
    {
        'id': 'qq',
        'name': 'QQ',
        'package': 'nonebot-adapter-qq',
        'module_name': 'nonebot.adapters.qq',
        'author': 'yanyongyu',
        'homepage': 'https://github.com/nonebot/adapter-qq',
        'is_official': True,
        'platforms': ['qq_client', 'qq_guild'],
        'description': 'QQ 开放平台官方机器人适配器。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.qq'],
        'config_keys': ['QQ_BOTS'],
    },
    {
        'id': 'telegram',
        'name': 'Telegram',
        'package': 'nonebot-adapter-telegram',
        'module_name': 'nonebot.adapters.telegram',
        'author': 'j1g5awi',
        'homepage': 'https://github.com/nonebot/adapter-telegram',
        'is_official': True,
        'platforms': ['telegram'],
        'description': 'Telegram Bot API 适配器。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.telegram'],
        'config_keys': ['TELEGRAM_BOTS'],
    },
    {
        'id': 'discord',
        'name': 'Discord',
        'package': 'nonebot-adapter-discord',
        'module_name': 'nonebot.adapters.discord',
        'author': 'CMHopeSunshine',
        'homepage': 'https://github.com/nonebot/adapter-discord',
        'is_official': True,
        'platforms': ['discord'],
        'description': 'Discord Gateway 与 Bot API 适配器。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.discord'],
        'config_keys': ['DISCORD_BOTS'],
    },
    {
        'id': 'dodo',
        'name': 'DoDo',
        'package': 'nonebot-adapter-dodo',
        'module_name': 'nonebot.adapters.dodo',
        'author': 'CMHopeSunshine',
        'homepage': 'https://github.com/nonebot/adapter-dodo',
        'is_official': True,
        'platforms': ['dodo'],
        'description': 'DoDo 开放平台适配器。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.dodo'],
        'config_keys': ['DODO_BOTS'],
    },
    {
        'id': 'kook',
        'name': 'Kook',
        'package': 'nonebot-adapter-kaiheila',
        'module_name': 'nonebot.adapters.kaiheila',
        'author': 'Tian-que',
        'homepage': 'https://github.com/Tian-que/nonebot-adapter-kaiheila',
        'is_official': False,
        'platforms': ['kook'],
        'description': 'KOOK（开黑啦）机器人适配器。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.kaiheila'],
        'config_keys': ['KAIHEILA_BOTS'],
    },
    {
        'id': 'satori',
        'name': 'Satori',
        'package': 'nonebot-adapter-satori',
        'module_name': 'nonebot.adapters.satori',
        'author': 'RF-Tar-Railt',
        'homepage': 'https://github.com/nonebot/adapter-satori',
        'is_official': True,
        'platforms': ['wechat', 'wecom'],
        'description': '连接 Koishi 等 Satori 服务；服务端上报的平台可由 Uninfo/Alconna 识别为微信或企业微信。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.satori'],
        'config_keys': ['SATORI_CLIENTS'],
    },
    {
        'id': 'minecraft',
        'name': 'Minecraft',
        'package': 'nonebot-adapter-minecraft',
        'module_name': 'nonebot.adapters.minecraft',
        'author': '17TheWord',
        'homepage': 'https://github.com/17TheWord/nonebot-adapter-minecraft',
        'is_official': False,
        'platforms': ['minecraft'],
        'description': 'Minecraft 通信适配器，支持 Rcon 与 WebSocket。',
        'drivers': ADAPTER_DRIVERS['nonebot.adapters.minecraft'],
        'config_keys': ['MINECRAFT_WS_URLS', 'MINECRAFT_ACCESS_TOKEN'],
    },
]

# 受保护的适配器模块，禁止通过 WebUI 卸载（UniBot 核心依赖）
PROTECTED_ADAPTER_MODULES: set[str] = {'nonebot.adapters.minecraft'}
