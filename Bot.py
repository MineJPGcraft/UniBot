import asyncio
import importlib
import signal
from pathlib import Path

import nonebot

from Scripts import Process
from Scripts.Logging import configure_handlers, configure_logging, logger

LOG_PATH = Path('Logs/')

# 在 NoneBot 初始化前配置日志处理器，保证启动早期日志格式统一
configure_handlers(LOG_PATH)
nonebot.init()
driver = nonebot.get_driver()


@driver.on_startup
async def startup() -> None:
    from Scripts.Config import config
    from Scripts.Extensions import extension_manager
    from Scripts.Managers import (
        machine_manager,
        version_manager,
        webui_manager,
    )

    machine_manager.init()

    asyncio.create_task(version_manager.init())
    asyncio.create_task(machine_manager.register())

    await extension_manager.start()

    if config.webui.enabled:
        from Scripts.Api.Limiter import rate_limiter
        from Scripts.Managers.Data import data_manager

        data_manager.load()
        rate_limiter.start()
        await webui_manager.init()


@driver.on_shutdown
async def shutdown() -> None:
    from Scripts.Extensions import extension_manager
    from Scripts.Managers import machine_manager
    from Scripts.Config import config

    await machine_manager.mark_offline()
    await extension_manager.shutdown()

    if config.webui.enabled:
        from Scripts.Api.Limiter import rate_limiter
        from Scripts.Managers.Data import data_manager
        
        rate_limiter.stop()
        await data_manager.save()


def register_adapters(driver, adapters: list[dict]) -> None:
    """注册已配置的 NoneBot 适配器，单个适配器加载失败不影响其他适配器。"""
    for adapter in adapters:
        module_name = adapter['module_name']
        try:
            module = importlib.import_module(module_name)
            adapter_class = getattr(module, 'Adapter', None)
            if adapter_class is None:
                logger.warning(f'Adapter module {module_name} does not contain an Adapter class, skipped.')
                continue
            logger.info(f'Registering <cyan>{adapter_class}</cyan> adapter.')
            driver.register_adapter(adapter_class)
        except Exception as error:
            logger.warning(f'Failed to load adapter {module_name}, skipped. Reason: {error}')


def load_plugins(plugins: list[str | dict]) -> None:
    """加载已启用的 NoneBot 插件。"""
    for plugin in plugins:
        if isinstance(plugin, str):
            nonebot.load_plugin(plugin)
            continue
        if (module_name := plugin.get('module_name', '')) and plugin.get('enabled', True):
            nonebot.load_plugin(module_name)


def exit_on_sigterm(_signal_number: int, _frame: object) -> None:
    """使用预期退出码结束机器人进程。"""
    raise SystemExit(Process.get_exit_code())


def main():
    """初始化并运行机器人进程。"""
    # NoneBot 初始化必须在本地模块导入之前完成。
    from Scripts.Config import config as bot_config
    from Scripts.Managers import config_manager, webui_manager

    configure_logging()
    config_manager.init()

    register_adapters(driver, config_manager.nonebot_config.get('adapters', []))

    nonebot.load_plugin('Scripts.Plugins.Extensions')
    load_plugins(config_manager.nonebot_config.get('plugins', []))

    if bot_config.webui.enabled:
        webui_manager.mount(nonebot.get_app())

    signal.signal(signal.SIGTERM, exit_on_sigterm)
    nonebot.run()


if __name__ == '__main__':
    main()
