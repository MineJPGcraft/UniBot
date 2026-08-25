"""全局常量集中收口：文件路径、扩展系统约定与内置插件前缀。

仅依赖标准库，任何模块都可安全导入（避免循环导入）。
"""

from pathlib import Path

# ===== 配置文件 =====
CONFIG_TOML_PATH = Path('Config.toml')
ENV_PATH = Path('.env')
PYPROJECT_PATH = Path('pyproject.toml')
# 消息文本双语包：按 Config.toml 的 language 字段选择加载（旧版单文件仅作中文包回退）
MESSAGES_ZH_PATH = Path('Config') / 'Messages.zh.toml'
MESSAGES_EN_PATH = Path('Config') / 'Messages.en.toml'
MESSAGES_LEGACY_PATH = Path('Config') / 'Messages.toml'

# ===== 运行时数据 =====
DATA_DIR = Path('Data')
STATISTICS_FILE = DATA_DIR / 'Statistics.json'

# ===== 扩展系统约定 =====
EXTENSIONS_DIR = Path('Extensions')
MANIFEST_FILE = 'Extension.toml'
# 扩展启停记录（enabled 标志，重启生效）
CONFIG_EXTENSIONS_FILE = Path('Config') / 'Extensions.toml'
# 市场数据缓存时长（秒），插件市场与扩展市场共用同一刷新周期
MARKET_CACHE_TTL = 600

# ===== 插件 =====
# 框架内置插件模块前缀：内置插件不允许经 WebUI 禁用或删除
BUILTIN_PLUGIN_PREFIX = 'Scripts.'

# ===== QQ 官方机器人事件订阅（Intent）字段 =====
# WebUI 表单与扫码登录默认订阅共用此清单（单一来源，防止两处漂移）
QQ_INTENT_FIELDS = [
    {'key': 'guilds', 'label': '频道事件', 'type': 'boolean', 'default': False},
    {'key': 'guild_members', 'label': '频道成员事件', 'type': 'boolean', 'default': False},
    {'key': 'guild_messages', 'label': '频道消息事件', 'type': 'boolean', 'default': False},
    {'key': 'guild_message_reactions', 'label': '频道消息表态事件', 'type': 'boolean', 'default': False},
    {'key': 'direct_message', 'label': '频道私信事件', 'type': 'boolean', 'default': False},
    {'key': 'open_forum_event', 'label': '频道公域论坛事件', 'type': 'boolean', 'default': False},
    {'key': 'audio_live_member', 'label': '频道音频或直播成员事件', 'type': 'boolean', 'default': False},
    {
        'key': 'c2c_group_at_messages',
        'label': '私聊与群聊 @ 消息事件',
        'type': 'boolean',
        'default': True,
    },
    {'key': 'interaction', 'label': '互动事件', 'type': 'boolean', 'default': False},
    {'key': 'message_audit', 'label': '频道消息审核事件', 'type': 'boolean', 'default': False},
    {'key': 'forum_event', 'label': '频道私域论坛事件', 'type': 'boolean', 'default': False},
    {'key': 'audio_action', 'label': '频道音频操作事件', 'type': 'boolean', 'default': False},
    {'key': 'at_messages', 'label': '频道 @ 机器人消息事件', 'type': 'boolean', 'default': False},
]

# ===== QQ 官方机器人开放接口（OpenAPI） =====
# 凭证与业务接口统一走 https://api.bot.qq.com（官方文档：获取访问凭证 / 自定义菜单与指令面板）
QQ_OPEN_API_BASE = 'https://api.bot.qq.com'
QQ_OPEN_API_TOKEN_PATH = '/app/getAppAccessToken'
QQ_OPEN_API_PANELS_PATH = '/v2/panels'
# access_token 有效期约 7200 秒，提前 5 分钟刷新
QQ_PANEL_TOKEN_REFRESH_MARGIN_SECONDS = 300
