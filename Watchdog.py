import hashlib
import os
import signal
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from Scripts.Constants import CONFIG_TOML_PATH, DATA_DIR, PYPROJECT_PATH
from Scripts.Logging import configure_handlers, logger
from Scripts.Process import RESTART_EXIT_CODE, WATCHDOG_ENVIRONMENT

MAX_RESTART_ATTEMPTS = 3
RESTART_WINDOW_SECONDS = 60

BOT_PATH = Path('Bot.py')
# 记录最近一次同步时的依赖指纹，用于判断依赖声明是否有变化
HASH_FILE = DATA_DIR / 'Project.hash'

EXTRA_CONFIG_FIELDS = {
    'webui': ('webui', 'enabled'),
}


def read_toml(path: Path) -> dict:
    """读取 TOML 文件。"""
    return tomllib.loads(path.read_text('Utf-8'))


def get_enabled_extras() -> list[str]:
    """获取当前配置中已启用的可选功能。"""
    config = read_toml(CONFIG_TOML_PATH)
    return [
        extra for extra, (section, field) in EXTRA_CONFIG_FIELDS.items() if config.get(section, {}).get(field, False)
    ]


def sync_dependencies() -> None:
    """使用 uv 同步项目依赖和已启用的可选功能。"""
    command = ['uv', 'sync']
    for extra in get_enabled_extras():
        command.extend(('--extra', extra))
    # 扩展依赖统一收口到 extensions 可选组
    command.extend(('--extra', 'extensions'))

    logger.info(f'Dependency declaration changed, running: {" ".join(command)}')
    try:
        subprocess.run(command, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        logger.error(f'Failed to sync project dependencies: {error}')
        raise SystemExit(1) from error
    logger.success('Project dependencies synced.')


def get_dependency_fingerprint() -> str:
    """计算影响 uv 同步结果的依赖指纹。

    指纹由 pyproject.toml 的完整内容与当前启用的 extras 共同决定，
    任一变化都会导致指纹不同，从而触发重新同步。
    """
    digest = hashlib.sha256()
    digest.update(PYPROJECT_PATH.read_bytes())
    for extra in get_enabled_extras():
        digest.update(extra.encode('Utf-8'))
    return digest.hexdigest()


def sync_if_changed() -> bool:
    """对比 Data 目录中的指纹文件，依赖声明有变化时同步并更新指纹。

    首次运行（无指纹文件）也会同步。返回是否执行了同步。
    """
    current = get_dependency_fingerprint()
    if HASH_FILE.exists():
        try:
            if HASH_FILE.read_text('Utf-8').strip() == current:
                return False
        except Exception as error:
            logger.warning(f'Failed to read dependency fingerprint file, will resync: {error}')
    sync_dependencies()
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(current, encoding='Utf-8')
    return True


def run() -> None:
    """守护机器人进程，处理异常退出与 WebUI 重启请求。"""
    configure_handlers()
    restart_attempts = 0
    restart_window_started_at = time.monotonic()
    shutdown_requested = False
    # 仅当依赖声明（pyproject.toml / 启用的 extras）发生变化时才同步，
    # 通过 Data 目录中的指纹文件判断，避免每次启动都执行 uv sync
    sync_if_changed()
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
            # WebUI 重启前对比指纹，依赖声明有变化则先同步再启动
            sync_if_changed()
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
