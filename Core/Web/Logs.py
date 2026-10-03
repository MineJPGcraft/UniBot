from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends

from Scripts.Api.Locale import text

from .Auth import get_current_user

router = APIRouter(prefix='/api/logs', tags=['Logs'])

LOGS_DIR = Path('Logs').resolve()


@router.get('', summary='获取日志文件列表')
async def get_logs(current_user: dict = Depends(get_current_user)):
    """获取日志文件列表。"""
    if not LOGS_DIR.exists():
        return {'code': 0, 'data': [], 'message': 'ok'}

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
    return {'code': 0, 'data': log_files, 'message': 'ok'}


@router.get('/{name}', summary='获取日志内容')
async def get_log_content(
    name: str,
    current_user: dict = Depends(get_current_user),
):
    """获取指定日志文件原始内容，解析与过滤由前端完成。"""
    if not name.endswith('.log'):
        return {'code': 1, 'data': None, 'message': text('logs.file_not_found')}
    log_file = (LOGS_DIR / name).resolve()
    try:
        log_file.relative_to(LOGS_DIR)
    except ValueError:
        return {'code': 1, 'data': None, 'message': text('logs.file_not_found')}
    if not log_file.is_file():
        return {'code': 1, 'data': None, 'message': text('logs.file_not_found')}

    try:
        content = log_file.read_text('Utf-8')
    except Exception as error:
        return {'code': 1, 'data': None, 'message': text('logs.read_failed', error=error)}

    lines = [{'line': index, 'text': line} for index, line in enumerate(content.splitlines(), start=1)]

    return {'code': 0, 'data': lines, 'message': 'ok'}
