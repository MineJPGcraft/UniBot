import asyncio
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends

from ..Locale import text
from .Auth import get_current_user

router = APIRouter(prefix='/api/logs', tags=['Logs'])

LOGS_DIR = Path('Logs').resolve()

# 单次返回的最大日志行数（默认只取末尾若干行，避免整文件读入内存与拖垮事件循环）
DEFAULT_LOG_LINES = 2000
MAX_LOG_LINES = 10000


def _list_log_files() -> list[dict]:
    """同步列出日志文件（阻塞 IO，调用方放入线程执行）。"""
    if not LOGS_DIR.exists():
        return []
    log_files = []
    for file in sorted(LOGS_DIR.glob('*.log'), reverse=True):
        file_stat = file.stat()
        log_files.append(
            {
                'name': file.name,
                'size': file_stat.st_size,
                'modified': datetime.fromtimestamp(file_stat.st_mtime, tz=UTC).isoformat(),
            }
        )
    return log_files


def _read_tail(log_file: Path, lines: int) -> list[dict]:
    """读取日志文件末尾若干行（同步阻塞 IO，调用方放入线程执行）。"""
    with log_file.open('r', encoding='Utf-8', errors='replace') as handle:
        tail = deque(handle, maxlen=lines)
    return [{'line': index, 'text': line} for index, line in enumerate(tail, start=1)]


@router.get('', summary='获取日志文件列表')
async def get_logs(current_user: dict = Depends(get_current_user)):
    """获取日志文件列表。"""
    return {'code': 0, 'data': await asyncio.to_thread(_list_log_files), 'message': 'ok'}


@router.get('/{name}', summary='获取日志内容')
async def get_log_content(
    name: str,
    lines: int = DEFAULT_LOG_LINES,
    current_user: dict = Depends(get_current_user),
):
    """获取指定日志文件末尾内容（`lines` 控制返回行数上限），解析与过滤由前端完成。"""
    if not name.endswith('.log'):
        return {'code': 1, 'data': None, 'message': text('logs.file_not_found')}
    log_file = (LOGS_DIR / name).resolve()
    try:
        log_file.relative_to(LOGS_DIR)
    except ValueError:
        return {'code': 1, 'data': None, 'message': text('logs.file_not_found')}
    if not log_file.is_file():
        return {'code': 1, 'data': None, 'message': text('logs.file_not_found')}

    limit = max(1, min(lines, MAX_LOG_LINES))
    try:
        data = await asyncio.to_thread(_read_tail, log_file, limit)
    except Exception as error:
        return {'code': 1, 'data': None, 'message': text('logs.read_failed', error=error)}

    return {'code': 0, 'data': data, 'message': 'ok'}
