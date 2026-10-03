from nonebot import require

require('nonebot_plugin_uninfo')
require('nonebot_plugin_alconna')

from Core.Config import config  # noqa: E402
from Core.Extension import command_manager, extension_manager  # noqa: E402
from Core.Extension.Manifest import set_unibot_version  # noqa: E402
from Core.Managers import config_manager  # noqa: E402

# Bootstrap 在扩展框架加载前注入当前版本号，供兼容性校验使用（框架不反向依赖 Managers）
set_unibot_version(config_manager.version.lstrip('v'))
# 注入图像模式读取器，使 CommandManager 无需顶层依赖 Core.Config
command_manager.set_image_mode_enabled(lambda: config.image.mode)
extension_manager.load()
command_manager.build()
