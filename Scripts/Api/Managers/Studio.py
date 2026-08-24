"""Extension Studio 管理器：下载、校验、启动、停止与日志查看。"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import platform
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil

from Scripts.Logging import exception_logger, logger
from Scripts.Network import download, request

# Studio 版本清单与下载地址（私有仓库经 bot-api 分发）
STUDIO_VERSION_URL = 'https://bot-api.mcjpg.dev/files/version.json'
STUDIO_DOWNLOAD_BASE = 'https://bot-api.mcjpg.dev/files/'

# Studio 数据目录名（相对 UniBot 根目录）
STUDIO_DIR_NAME = '.studio'
# 运行状态记录文件
PID_FILE_NAME = 'studio.pid'
VERSION_FILE_NAME = '.version'
# Studio 进程日志文件（stdout/stderr 重定向）
LOG_FILE_NAME = 'studio.log'
# Studio 自身日志目录（数据目录下，含就绪地址）
STUDIO_LOGS_DIR_NAME = 'logs'
STUDIO_LOG_FILE_NAME = 'studio.log'

# 就绪日志：已就绪：http://127.0.0.1:{port}/?token={token}（Ctrl+C 停止）
# URL 后紧跟中文括号，需在括号前截断
READY_URL_PATTERN = re.compile(r'已就绪：\s*(https?://\S+?)(?=[（(]|$)')

# UniBot 根目录（Bot.py 所在目录）
UNIBOT_ROOT = Path(__file__).resolve().parent.parent.parent


def _platform_asset_name() -> str:
    """根据当前平台返回 version.json 中的资源文件名。"""
    system = sys.platform
    machine = platform.machine().lower()
    if system == 'darwin':
        return 'unibot-studio-macos-arm64' if machine in ('arm64', 'aarch64') else 'unibot-studio-macos-x64'
    if system in ('linux', 'freebsd'):
        return 'unibot-studio-linux-x64'
    if system == 'win32':
        return 'unibot-studio-windows-x64.exe'
    raise RuntimeError(f'Unsupported platform: {system} {machine}')


class StudioManager:
    """Extension Studio 管理器单例。"""

    def __init__(self) -> None:
        self.studio_dir = UNIBOT_ROOT / STUDIO_DIR_NAME
        self.asset_name = _platform_asset_name()

    # ===== 状态 =====

    def executable_path(self) -> Path:
        """返回 Studio 可执行文件路径。"""
        return self.studio_dir / self.asset_name

    def is_downloaded(self) -> bool:
        """判断 Studio 是否已下载（可执行文件存在）。"""
        return self.executable_path().is_file()

    def read_local_version(self) -> str:
        """读取本地已下载的 Studio 版本。"""
        version_file = self.studio_dir / VERSION_FILE_NAME
        if version_file.exists():
            return version_file.read_text('Utf-8').strip()
        return ''

    def is_running(self) -> bool:
        """判断 Studio 进程是否在运行（PID 文件 + 进程名校验）。"""
        pid_file = self.studio_dir / PID_FILE_NAME
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text('Utf-8').strip())
            if not psutil.pid_exists(pid):
                return False
            return 'unibot-studio' in psutil.Process(pid).name().lower()
        except (ValueError, psutil.Error):
            return False

    def status(self) -> dict:
        """返回 Studio 状态（供 WebUI 展示）。"""
        return {
            'installed': self.is_downloaded(),
            'version': self.read_local_version(),
            'running': self.is_running(),
            'url': self.read_ready_url() if self.is_running() else '',
        }

    def read_ready_url(self) -> str:
        """
        从日志中解析 Studio 就绪地址（含登录 token）。

        优先返回带 token 的地址（新版本格式）；旧版本日志无 token 时回退到
        最后一个就绪地址，避免命中历史无 token 行。
        """
        matches: list[str] = []
        for log_file in self._log_candidates():
            if not log_file.exists():
                continue
            try:
                content = log_file.read_text('Utf-8', errors='replace')
            except OSError:
                continue
            matches.extend(READY_URL_PATTERN.findall(content))
        if not matches:
            return ''
        for url in reversed(matches):
            if 'token=' in url:
                return url
        return matches[-1]

    def _log_candidates(self) -> list[Path]:
        """候选日志文件：优先 WebUI 重定向日志，其次 Studio 自身日志。"""
        return [
            self.studio_dir / LOG_FILE_NAME,
            self.studio_dir / STUDIO_LOGS_DIR_NAME / STUDIO_LOG_FILE_NAME,
        ]

    async def wait_ready(self, timeout: float = 30.0) -> str:
        """等待 Studio 就绪并返回访问地址（含 token），超时返回空串。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            url = self.read_ready_url()
            if url:
                return url
            await asyncio.sleep(0.5)
        return ''

    # ===== 下载 =====

    async def ensure_downloaded(self) -> tuple[bool, str]:
        """确保 Studio 已下载到 .studio 目录，返回 (成功, 消息)。"""
        if self.is_downloaded():
            return True, 'Studio 已下载'
        try:
            release = await request(STUDIO_VERSION_URL)
            if not isinstance(release, dict):
                return False, '获取 Studio 版本信息失败'
            files = release.get('files', {})
            expected_sha256 = files.get(self.asset_name, '')
            if not expected_sha256:
                return False, f'版本清单中不存在当前平台的 Studio 文件：{self.asset_name}'
            url = STUDIO_DOWNLOAD_BASE + self.asset_name
            response = await download(url)
            if response is None:
                return False, f'下载 Studio 失败：{url}'
            archive_data = response.getvalue()
            actual_sha256 = hashlib.sha256(archive_data).hexdigest()
            if actual_sha256.lower() != expected_sha256.lower():
                return False, 'Studio 文件校验失败（sha256 不匹配）'
            self.studio_dir.mkdir(parents=True, exist_ok=True)
            executable = self.executable_path()
            executable.write_bytes(archive_data)
            executable.chmod(0o755)
            release_tag = release.get('release_tag', '')
            (self.studio_dir / VERSION_FILE_NAME).write_text(release_tag, encoding='Utf-8')
            logger.success(f'Extension Studio downloaded ({release_tag}).')
            return True, f'Studio 下载完成（{release_tag}）'
        except Exception as error:
            exception_logger.error('Failed to download Extension Studio!')
            return False, f'Studio 下载失败：{error}'

    # ===== 启动 / 停止 =====

    async def launch(self) -> tuple[bool, str]:
        """启动 Studio（数据目录 .studio，UniBot 目录为根目录），等待就绪并返回访问地址。"""
        if self.is_running():
            ready_url = self.read_ready_url()
            if ready_url:
                return True, ready_url
            return True, 'Studio 已在运行'
        if not self.is_downloaded():
            return False, 'Studio 尚未下载'
        executable = self.executable_path()
        command = [
            str(executable),
            '--data',
            str(self.studio_dir),
            '--unibot',
            str(UNIBOT_ROOT),
        ]
        try:
            self.studio_dir.mkdir(parents=True, exist_ok=True)
            log_file = self.studio_dir / LOG_FILE_NAME
            # 异步创建子进程，避免阻塞事件循环；日志句柄由子进程持有，父进程随即释放
            with log_file.open('ab') as log_stream:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=str(UNIBOT_ROOT),
                    stdout=log_stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            (self.studio_dir / PID_FILE_NAME).write_text(str(process.pid), encoding='Utf-8')
            logger.success(f'Extension Studio launched (pid={process.pid}).')
            ready_url = await self.wait_ready()
            if ready_url:
                return True, ready_url
            return True, 'Studio 已启动'
        except Exception as error:
            exception_logger.error('Failed to launch Extension Studio!')
            return False, f'Studio 启动失败：{error}'

    async def stop(self) -> tuple[bool, str]:
        """停止 Studio 进程并清理 PID 状态文件（阻塞等待放入线程）。"""
        pid_file = self.studio_dir / PID_FILE_NAME
        if not pid_file.exists():
            return False, 'Studio 未在运行'
        try:
            pid = int(pid_file.read_text('Utf-8').strip())
        except ValueError:
            return False, 'Studio 状态文件异常'
        try:
            success = await asyncio.to_thread(self._terminate_process, pid)
            if not success:
                return False, 'Studio 停止失败'
        except Exception as error:
            exception_logger.error('Failed to stop Extension Studio!')
            return False, f'Studio 停止失败：{error}'
        self._cleanup_state_files()
        logger.success(f'Extension Studio stopped (pid={pid}).')
        return True, 'Studio 已停止'

    @staticmethod
    def _terminate_process(pid: int) -> bool:
        """终止 Studio 进程：先优雅终止，超时后强杀。"""
        try:
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                if 'unibot-studio' in process.name().lower():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        process.kill()
            else:
                os.kill(pid, signal.SIGTERM)
        except (psutil.Error, ProcessLookupError):
            pass
        except Exception:
            return False
        return True

    def read_log(self, tail: int = 200) -> str:
        """读取 Studio 进程日志（默认返回末尾 tail 行）。"""
        for log_file in self._log_candidates():
            if not log_file.exists():
                continue
            try:
                lines = log_file.read_text('Utf-8', errors='replace').splitlines()
            except OSError:
                continue
            if lines:
                return '\n'.join(lines[-tail:])
        return ''

    def _cleanup_state_files(self) -> None:
        """清理 PID 状态文件。"""
        pid_file = self.studio_dir / PID_FILE_NAME
        if pid_file.exists():
            with contextlib.suppress(OSError):
                pid_file.unlink()


studio_manager = StudioManager()
