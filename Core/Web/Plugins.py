from enum import StrEnum

from fastapi import APIRouter, Depends, Query

from Scripts.Api.Locale import text
from Scripts.Constants import (
    BUILTIN_PLUGIN_PREFIX,
    TaskKind,
    UserRole,
)
from Scripts.Extensions.Dependencies import apply_main_dependency_changes
from Scripts.Managers import config_manager, plugin_manager, task_center
from Scripts.Managers.TaskCenter import TaskContext

from .Auth import get_current_user, require_role
from .Schemas import InstallPluginRequest, UpgradePluginRequest

router = APIRouter(prefix='/api/plugins', tags=['Plugins'])


class PluginMarketAction(StrEnum):
    """插件市场操作类型。"""

    install = 'install'
    upgrade = 'upgrade'
    uninstall = 'uninstall'


# 市场动作 → (任务类型, 阶段消息键, 完成消息键)
MARKET_ACTIONS = {
    PluginMarketAction.install: (
        TaskKind.plugin_install,
        'task_center.msg_installing_plugin',
        'task_center.msg_plugin_installed',
    ),
    PluginMarketAction.upgrade: (
        TaskKind.plugin_upgrade,
        'task_center.msg_upgrading_plugin',
        'task_center.msg_plugin_upgraded',
    ),
    PluginMarketAction.uninstall: (
        TaskKind.plugin_uninstall,
        'task_center.msg_uninstalling_plugin',
        'task_center.msg_plugin_uninstalled',
    ),
}


async def run_plugin_market_task(
    context: TaskContext,
    action: PluginMarketAction,
    project_link: str,
    module_name: str,
    version: str,
) -> str:
    """任务体：登记/移除插件登记，并用 uv 安装、更新或移除其依赖包。"""
    _, running_key, finished_key = MARKET_ACTIONS[action]
    context.set_message(running_key, name=module_name)

    if action == PluginMarketAction.uninstall:
        config_manager.remove_plugin(module_name)
    else:
        config_manager.add_plugin(module_name)
        if action == PluginMarketAction.upgrade:
            config_manager.set_plugin_enabled(module_name, True)

    removing = action == PluginMarketAction.uninstall
    package = f'{project_link}=={version}' if version else project_link
    context.set_message('task_center.msg_syncing_dependencies')
    await apply_main_dependency_changes(
        [] if removing else [package],
        [project_link] if removing else [],
        context.log,
    )

    # 同步插件管理器的市场缓存状态
    await plugin_manager.fetch_market(force=True)
    # 新装/升级/卸载的插件都要重启后才会被 NoneBot 加载或彻底卸载
    context.set_result(restart_required=True)
    return finished_key


def submit_plugin_market(
    action: PluginMarketAction,
    project_link: str,
    module_name: str,
    version: str = '',
) -> dict:
    """提交插件市场操作任务（install / upgrade / uninstall）。"""
    kind = MARKET_ACTIONS.get(action, MARKET_ACTIONS[PluginMarketAction.install])[0]
    return task_center.submit(
        kind,
        lambda context: run_plugin_market_task(context, action, project_link, module_name, version),
        title_params={'name': module_name},
    )


@router.get('', summary='获取已安装插件列表')
async def get_plugins(current_user: dict = Depends(get_current_user)):
    """获取所有已安装插件。"""
    return {'code': 0, 'data': plugin_manager.get_installed_plugins(), 'message': 'ok'}


async def find_market_plugin(name: str) -> dict | None:
    """在插件市场中按 project_link / module_name 查找插件。"""
    items = await plugin_manager.fetch_market()
    return next(
        (item for item in items if item.get('project_link') == name or item.get('module_name') == name),
        None,
    )


def installed_state(items: list[dict]) -> list[dict]:
    """标注市场插件是否已安装 / 已登记。"""
    installed_packages = {config_manager._package_base(dependency) for dependency in config_manager.get_dependencies()}
    registered_modules = {
        plugin.get('module_name') if isinstance(plugin, dict) else plugin
        for plugin in config_manager.nonebot_config.get('plugins', [])
    }
    result = []
    for item in items:
        project_link = item.get('project_link', '')
        module_name = item.get('module_name', '')
        result.append(
            {
                'module_name': module_name,
                'project_link': project_link,
                'name': item.get('name', ''),
                'desc': item.get('desc', ''),
                'author': item.get('author', ''),
                'homepage': item.get('homepage', ''),
                'tags': item.get('tags', []),
                'is_official': item.get('is_official', False),
                'type': item.get('type', ''),
                'supported_adapters': item.get('supported_adapters') or [],
                'version': item.get('version', ''),
                'time': item.get('time', ''),
                'installed': project_link in installed_packages,
                'registered': module_name in registered_modules,
            }
        )
    return result


@router.get('/market', summary='插件市场')
async def get_market(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(''),
    category: str = Query(''),
    current_user: dict = Depends(get_current_user),
):
    """从远程注册表获取可用插件列表，支持搜索与分类筛选。"""
    items = await plugin_manager.fetch_market()
    keyword = keyword.strip().lower()
    if keyword:
        items = [
            item
            for item in items
            if keyword in (item.get('name') or '').lower()
            or keyword in (item.get('project_link') or '').lower()
            or keyword in (item.get('module_name') or '').lower()
            or keyword in (item.get('desc') or '').lower()
        ]
    if category:
        items = [item for item in items if any(tag.get('label') == category for tag in item.get('tags') or [])]
    result_items = installed_state(items)
    total = len(result_items)
    start = (page - 1) * page_size
    return {
        'code': 0,
        'data': {
            'items': result_items[start : start + page_size],
            'total': total,
            'page': page,
            'page_size': page_size,
        },
        'message': 'ok',
    }


@router.post('/market/install', summary='安装插件')
async def install_plugin(body: InstallPluginRequest, current_user: dict = Depends(require_role(UserRole.admin))):
    """提交插件安装任务（登记依赖并用 uv 安装），进度在任务中心查看。"""
    plugin = await find_market_plugin(body.name)
    if not plugin:
        return {'code': 1, 'data': None, 'message': text('plugins.market_not_found')}
    task = submit_plugin_market(
        PluginMarketAction.install, plugin['project_link'], plugin['module_name'], body.version
    )
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}


@router.post('/market/upgrade', summary='升级插件')
async def upgrade_plugin(body: UpgradePluginRequest, current_user: dict = Depends(require_role(UserRole.admin))):
    """提交插件升级任务（更新登记并用 uv 安装），进度在任务中心查看。"""
    plugin = await find_market_plugin(body.name)
    if not plugin:
        return {'code': 1, 'data': None, 'message': text('plugins.market_not_found')}
    task = submit_plugin_market(PluginMarketAction.upgrade, plugin['project_link'], plugin['module_name'])
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}


@router.get('/{name}', summary='获取插件详情')
async def get_plugin_detail(name: str, current_user: dict = Depends(get_current_user)):
    """获取指定插件详情。"""
    detail = plugin_manager.get_plugin_detail(name)
    if not detail:
        return {'code': 1, 'data': None, 'message': text('plugins.not_found')}
    return {'code': 0, 'data': detail, 'message': 'ok'}


@router.post('/{name}/enable', summary='启用插件')
async def enable_plugin(name: str, current_user: dict = Depends(require_role(UserRole.admin))):
    """启用插件。"""
    success = await plugin_manager.set_enabled(name, True)
    if not success:
        return {'code': 1, 'data': None, 'message': text('plugins.not_found')}
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.post('/{name}/disable', summary='禁用插件')
async def disable_plugin(name: str, current_user: dict = Depends(require_role(UserRole.admin))):
    """禁用插件。"""
    success = await plugin_manager.set_enabled(name, False)
    if not success:
        return {'code': 1, 'data': None, 'message': text('plugins.not_found')}
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.delete('/{name}', summary='卸载插件')
async def uninstall_plugin(name: str, current_user: dict = Depends(require_role(UserRole.admin))):
    """提交插件卸载任务（移除登记并用 uv 卸载依赖），进度在任务中心查看。"""
    plugin = plugin_manager.get_plugin_detail(name)
    if not plugin:
        return {'code': 1, 'data': None, 'message': text('plugins.not_found')}
    module_name = plugin['module_name']
    if module_name.startswith(BUILTIN_PLUGIN_PREFIX):
        return {'code': 1, 'data': None, 'message': text('plugins.builtin_cannot_uninstall')}
    # 在市场中查找对应的 PyPI 包名
    market_plugin = await find_market_plugin(module_name)
    project_link = market_plugin.get('project_link', '') if market_plugin else ''
    # 未收录于市场时按模块名作为包名走 uv remove（依赖写入只经 uv，不手改 pyproject）
    task = submit_plugin_market(PluginMarketAction.uninstall, project_link or module_name, module_name)
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}
