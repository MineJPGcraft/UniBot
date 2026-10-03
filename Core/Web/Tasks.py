"""后台任务中心 WebUI 路由：任务列表、详情、取消与重试。"""

from fastapi import APIRouter, Depends, HTTPException

from Scripts.Api.Locale import text
from Scripts.Constants import TaskKind, UserRole
from Scripts.Extensions.Dependencies import sync_extension_dependencies
from Scripts.Managers import task_center
from Scripts.Managers.TaskCenter import TaskContext

from .Auth import get_current_user, require_role

router = APIRouter(prefix='/api/tasks', tags=['Tasks'])


async def run_sync_task(context: TaskContext) -> str:
    """任务体：按扩展声明经 uv add / uv remove 同步依赖，并执行 uv sync。"""
    context.log('Starting dependency synchronization...')
    await sync_extension_dependencies(context.log)
    context.raise_if_cancelled()
    return 'task_center.msg_dependencies_synced'


@router.get('', summary='任务列表')
async def list_tasks(current_user: dict = Depends(get_current_user)):
    """返回全部后台任务快照（按创建时间倒序）与进行中统计。"""
    return {
        'code': 0,
        'data': {'items': task_center.list_tasks(), 'summary': task_center.summary()},
        'message': 'ok',
    }


@router.get('/{task_id}', summary='任务详情')
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """返回单个任务详情（含完整日志）。"""
    record = task_center.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=text('task_center.not_found'))
    return {'code': 0, 'data': record.snapshot(with_logs=True), 'message': 'ok'}


@router.post('/{task_id}/cancel', summary='取消任务')
async def cancel_task(task_id: str, user: dict = Depends(require_role(UserRole.admin))):
    """请求取消指定任务（任务体在长流程中主动检查取消标志）。"""
    if task_center.get(task_id) is None:
        raise HTTPException(status_code=404, detail=text('task_center.not_found'))
    success, message = task_center.cancel(task_id)
    if success:
        return {'code': 0, 'data': None, 'message': text(message)}
    return {'code': 1, 'data': None, 'message': text(message)}


@router.post('/{task_id}/retry', summary='重试任务')
async def retry_task(task_id: str, user: dict = Depends(require_role(UserRole.admin))):
    """以同一任务体重新提交任务。"""
    if task_center.get(task_id) is None:
        raise HTTPException(status_code=404, detail=text('task_center.not_found'))
    success, message = task_center.retry(task_id)
    if success:
        return {'code': 0, 'data': None, 'message': text(message)}
    return {'code': 1, 'data': None, 'message': text(message)}


@router.post('/dependency-sync', summary='手动同步依赖')
async def sync_dependencies(user: dict = Depends(require_role(UserRole.admin))):
    """提交依赖同步任务：按扩展声明 uv add / uv remove 并 uv sync。"""
    snapshot = task_center.submit(
        TaskKind.dependency_sync,
        run_sync_task,
        message_key='task_center.msg_syncing_dependencies',
    )
    return {'code': 0, 'data': snapshot, 'message': text('task_center.submitted')}
