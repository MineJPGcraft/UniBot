import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from Scripts.Logging import configure_handlers, logger, print_banner
from Scripts.Process import RESTART_EXIT_CODE, WATCHDOG_ENVIRONMENT

MAX_RESTART_ATTEMPTS = 3
RESTART_WINDOW_SECONDS = 60

BOT_PATH = Path('Bot.py')


def run() -> None:
    """守护机器人进程，处理异常退出与 WebUI 重启请求。"""
    configure_handlers()
    # 横幅仅在守护进程启动时打印一次，Bot 子进程重启时不再重复输出
    print_banner()
    restart_attempts = 0
    restart_window_started_at = time.monotonic()
    shutdown_requested = False
    # 依赖同步已交由 Bot 进程内的任务中心执行（见 Scripts/Plugins/Extensions.py），
    # 守护进程只负责进程保活与重启，不再执行 uv sync
    bot_environment = os.environ.copy()
    bot_environment[WATCHDOG_ENVIRONMENT] = '1'

    while True:
        bot_process = subprocess.Popen(
            [sys.executable, str(BOT_PATH), *sys.argv[1:]],
            env=bot_environment,
            start_new_session=True,
        )

        def forward_signal(signal_number: int, _frame: object) -> None:
            nonlocal shutdown_requested
            shutdown_requested = True
            if bot_process.poll() is None:
                bot_process.send_signal(signal_number)

        signal.signal(signal.SIGINT, forward_signal)
        signal.signal(signal.SIGTERM, forward_signal)
        exit_code = bot_process.wait()

        if exit_code == RESTART_EXIT_CODE:
            restart_attempts = 0
            restart_window_started_at = time.monotonic()
            logger.info('WebUI restart requested, restarting the bot.')
            continue

        if shutdown_requested or exit_code in (0, -signal.SIGINT, -signal.SIGTERM):
            logger.info('Bot exited normally, not restarting.')
            return

        current_time = time.monotonic()
        if current_time - restart_window_started_at > RESTART_WINDOW_SECONDS:
            restart_window_started_at = current_time
            restart_attempts = 0

        if restart_attempts >= MAX_RESTART_ATTEMPTS:
            logger.error(
                f'Bot retried {MAX_RESTART_ATTEMPTS} times within {RESTART_WINDOW_SECONDS}s, giving up restarting.'
            )
            raise SystemExit(exit_code)

        restart_attempts += 1
        logger.warning(f'Bot exited abnormally (exit code {exit_code}), auto-restart attempt {restart_attempts}.')


if __name__ == '__main__':
    run()
