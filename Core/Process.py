import os
import signal

RESTART_EXIT_CODE = 75
WATCHDOG_ENVIRONMENT = 'UNIBOT_WATCHDOG'
DEV_ENVIRONMENT = 'UNIBOT_DEV'

_FALSE_VALUES = frozenset({'0', 'false', 'no', 'off'})

exit_code = 0


def is_watchdog_process() -> bool:
    """检查当前机器人是否由守护进程启动。"""
    return os.environ.get(WATCHDOG_ENVIRONMENT) == '1'


def is_dev_mode() -> bool:
    """检查是否处于开发模式。

    取值优先级：进程环境变量 `UNIBOT_DEV` → `.env` 中的同名配置
    （NoneBot 只读取 `.env` 而不写回 `os.environ`，因此需要显式回退）。
    开发模式下 WebUI 前端由 Vite dev server（`bun run dev`）提供，
    后端只挂载 `/webui/api` 路由，不再托管本地构建产物。
    """
    value = os.environ.get(DEV_ENVIRONMENT, '').strip() or _read_dotenv(DEV_ENVIRONMENT)
    normalized = value.strip().lower()
    return bool(normalized) and normalized not in _FALSE_VALUES


def _read_dotenv(key: str) -> str:
    """从 `.env` 读取配置值；未初始化或读取失败时返回空串。"""
    try:
        from Core.Managers.Config import config_manager

        return str(config_manager.read_env().get(key) or '')
    except (Exception, SystemExit):
        return ''


def get_exit_code() -> int:
    """获取机器人进程的预期退出码。"""
    return exit_code


def request_restart() -> None:
    """记录重启退出码，并触发框架优雅关闭。

    必须使用 signal.raise_signal 而非 os.kill：Windows 上 os.kill 对除
    CTRL_C_EVENT / CTRL_BREAK_EVENT 之外的信号一律走 TerminateProcess，
    进程会被直接杀死且退出码被设为信号值（15），守护进程因此识别不到
    约定的重启码 75。raise_signal 在 Windows 上走 CRT raise，能正常触发
    已注册的信号处理器并保留 SystemExit 携带的退出码。
    """
    global exit_code
    exit_code = RESTART_EXIT_CODE
    signal.raise_signal(signal.SIGTERM)
