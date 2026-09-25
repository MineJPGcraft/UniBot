"""扩展系统 WebUI REST 路由：已安装扩展、配置、启停、渲染引擎与主题。"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from Scripts.Api.Locale import text
from Scripts.Api.Managers import studio_manager
from Scripts.Config import config, reload_config
from Scripts.Constants import TaskKind, UserRole
from Scripts.Extensions import EXTENSIONS_DIR, ExtensionState, ExtensionType, extension_manager, market_manager
from Scripts.Extensions.Dependencies import sync_extension_dependencies
from Scripts.Managers import config_manager, task_center
from Scripts.Managers.TaskCenter import TaskContext

from .Auth import get_current_user, require_role
from .Body import parse_json_object
from .Schemas import MarketInstallRequest, NameSwitchRequest

router = APIRouter(prefix='/api/extensions', tags=['Extensions'])


async def run_extension_install_task(context: TaskContext, extension_id: str, version: str, name: str) -> str:
    """任务体：下载安装扩展 → 同步依赖 → 热重载使其立即生效。"""
    context.set_message('task_center.msg_downloading_extension', name=name)
    success, message = await market_manager.install(extension_id, version)
    if not success:
        raise RuntimeError(message)
    context.log(message)

    context.set_message('task_center.msg_syncing_dependencies')
    await sync_extension_dependencies(context.log)

    context.log('Reloading extensions...')
    await extension_manager.reload()
    return 'task_center.msg_extension_installed'


async def run_extension_uninstall_task(context: TaskContext, extension_id: str, name: str) -> str:
    """任务体：卸载扩展 → 移除不再需要的依赖 → 热重载使其从注册表移除。"""
    context.set_message('task_center.msg_uninstalling_extension', name=name)
    success, message = await market_manager.uninstall(extension_id)
    if not success:
        raise RuntimeError(message)
    context.log(message)

    context.set_message('task_center.msg_syncing_dependencies')
    await sync_extension_dependencies(context.log)

    context.log('Reloading extensions...')
    await extension_manager.reload()
    return 'task_center.msg_extension_uninstalled'


async def run_extension_reload_task(context: TaskContext) -> str:
    """任务体：热重载全部扩展。"""
    context.log('Reloading all extensions...')
    await extension_manager.reload()
    return 'task_center.msg_extensions_reloaded'


async def run_studio_launch_task(context: TaskContext) -> str:
    """任务体：下载（如缺失）并启动 Extension Studio，产出访问地址。"""
    context.set_message('task_center.msg_studio_preparing')
    success, message = await studio_manager.ensure_downloaded()
    if not success:
        raise RuntimeError(message)
    context.log(message)

    context.set_message('task_center.msg_studio_launching')
    success, message = await studio_manager.launch()
    if not success:
        raise RuntimeError(message)

    url = message if message.startswith('http') else ''
    if url:
        context.set_result(url=url)
    context.log(f'Extension Studio ready: {url or message}')
    return 'task_center.msg_studio_launched'

# 图片模式必需的扩展（渲染引擎 + 默认模板包）。这些扩展随官方市场分发而非内置，
# 开启 image.mode 时若缺失，由 WebUI 引导用户自动下载。
IMAGE_MODE_REQUIRED_EXTENSIONS = [
    ('Html2Pic', 'Html2Pic 渲染引擎'),
    ('Default', '默认模板 & 资源'),
]

# 密钥字段脱敏占位符：前端原样回传时视为“未修改”，服务端还原为当前真实值
MASKED_PLACEHOLDER = '<configured>'


def _extension_downloaded(extension_id: str) -> bool:
    """判断扩展是否已下载（扩展目录存在且含 Extension.toml 清单）。"""
    return (EXTENSIONS_DIR / extension_id / 'Extension.toml').is_file()


def _mask_config(extension) -> dict:
    """获取扩展配置并脱敏密钥字段（只返回“已配置”状态）。"""
    if not extension.is_bound:
        return {}
    raw = extension.config.value.model_dump()
    masked = {}
    for key, value in raw.items():
        masked[key] = value
        if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower():
            masked[key] = MASKED_PLACEHOLDER if value else ''
    return masked


def _restore_masked(current: dict, patch_data: dict) -> dict:
    """把前端回传的脱敏占位符还原为当前真实值，避免仅修改其它字段时覆盖密钥。"""
    restored = {}
    for key, value in patch_data.items():
        if value == MASKED_PLACEHOLDER and key in current:
            restored[key] = current[key]
            continue
        restored[key] = value
    return restored


def _ensure_extension_exists(extension_id: str) -> None:
    """校验扩展存在（registry 或无代码包），否则抛 404。"""
    if extension_id in extension_manager.registry:
        return
    if extension_id in extension_manager.no_code_info:
        return
    raise HTTPException(status_code=404, detail=text('extensions.not_found', extension_id=extension_id))


@router.get('', summary='已安装扩展列表')
async def get_extensions(current_user: dict = Depends(get_current_user)):
    """获取已安装扩展列表（类型/版本/状态）。"""
    return {'code': 0, 'data': extension_manager.get_extensions(), 'message': 'ok'}


@router.get('/market', summary='扩展市场列表')
async def get_market(force: bool = False, current_user: dict = Depends(get_current_user)):
    """获取扩展市场注册表（带缓存），支持 force 强制刷新。"""
    data = await market_manager.fetch_market(force=force)
    return {'code': 0, 'data': data, 'message': 'ok'}


@router.post('/market/install', summary='从市场安装扩展')
async def install_market_extension(body: MarketInstallRequest, user: dict = Depends(require_role(UserRole.admin))):
    """提交扩展安装任务（后台下载 + 依赖同步），进度在任务中心查看。"""
    if not body.id:
        return {'code': 1, 'data': None, 'message': text('extensions.missing_id')}
    name = body.id
    if entry := market_manager.market_cache.get(body.id):
        name = entry.name or body.id
    task = task_center.submit(
        TaskKind.extension_install,
        lambda context: run_extension_install_task(context, body.id, body.version, name),
        title_params={'name': name},
    )
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}


@router.get('/image-requirements', summary='图片模式依赖扩展检查')
async def get_image_requirements(current_user: dict = Depends(get_current_user)):
    """返回图片模式所需扩展的下载情况，供开启图片模式时引导自动下载。"""
    # 确保市场缓存已加载，便于判断缺失扩展是否可从市场自动安装
    await market_manager.fetch_market()
    required = []
    missing = []
    for extension_id, display_name in IMAGE_MODE_REQUIRED_EXTENSIONS:
        installed = _extension_downloaded(extension_id)
        in_market = extension_id in market_manager.market_cache
        required.append(
            {
                'id': extension_id,
                'name': display_name,
                'installed': installed,
                'in_market': in_market,
            }
        )
        if not installed:
            missing.append(extension_id)
    return {
        'code': 0,
        'data': {
            'mode': config.image.mode,
            'required': required,
            'missing': missing,
        },
        'message': 'ok',
    }


@router.get('/studio', summary='Extension Studio 状态')
async def get_studio_status(current_user: dict = Depends(get_current_user)):
    """返回 Extension Studio 的下载与运行状态。"""
    return {'code': 0, 'data': studio_manager.status(), 'message': 'ok'}


@router.post('/studio/launch', summary='下载并启动 Extension Studio')
async def launch_studio(user: dict = Depends(require_role(UserRole.admin))):
    """提交 Studio 启动任务（后台下载与启动），进度在任务中心查看。"""
    task = task_center.submit(TaskKind.studio_launch, run_studio_launch_task, retryable=False)
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}


@router.post('/studio/stop', summary='停止 Extension Studio')
async def stop_studio(user: dict = Depends(require_role(UserRole.admin))):
    """停止 Studio 进程并清理状态文件。"""
    success, message = await studio_manager.stop()
    return {'code': 0 if success else 1, 'data': None, 'message': message}


@router.get('/studio/log', summary='Extension Studio 日志')
async def get_studio_log(tail: int = 200, current_user: dict = Depends(get_current_user)):
    """返回 Studio 进程日志（默认末尾 200 行）。"""
    content = await asyncio.to_thread(studio_manager.read_log, tail=tail)
    return {'code': 0, 'data': {'content': content}, 'message': 'ok'}


@router.get('/items/{extension_id}', summary='扩展详情与配置 schema')
async def get_extension_detail(extension_id: str, current_user: dict = Depends(get_current_user)):
    """获取扩展详情 + 配置 schema（供 WebUI 动态表单，含无代码模板包）。"""
    detail = extension_manager.get_extension_info(extension_id)
    if not detail:
        raise HTTPException(status_code=404, detail=text('extensions.not_found', extension_id=extension_id))
    return {'code': 0, 'data': detail, 'message': 'ok'}


@router.post('/reload', summary='热重载扩展')
async def reload_extensions(user: dict = Depends(require_role(UserRole.admin))):
    """提交扩展热重载任务（后台重载，进度在任务中心查看）。"""
    task = task_center.submit(TaskKind.extension_reload, run_extension_reload_task, retryable=False)
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}


@router.post('/{extension_id}/enable', summary='启用扩展')
async def enable_extension(extension_id: str, user: dict = Depends(require_role(UserRole.admin))):
    """启用扩展（写 Config/Extensions.toml，重启生效）。"""
    _ensure_extension_exists(extension_id)
    await asyncio.to_thread(extension_manager.set_enabled, extension_id, True)
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.post('/{extension_id}/disable', summary='禁用扩展')
async def disable_extension(extension_id: str, user: dict = Depends(require_role(UserRole.admin))):
    """禁用扩展（写 Config/Extensions.toml，重启生效）。"""
    _ensure_extension_exists(extension_id)
    await asyncio.to_thread(extension_manager.set_enabled, extension_id, False)
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.get('/{extension_id}/config', summary='读取扩展配置')
async def get_extension_config(extension_id: str, current_user: dict = Depends(get_current_user)):
    """读取扩展配置（密钥字段脱敏；无代码模板包读模板配置）。"""
    extension = extension_manager.registry.get(extension_id)
    if extension is not None:
        return {'code': 0, 'data': _mask_config(extension), 'message': 'ok'}
    registration = extension_manager.renderer_manager.templates.get(extension_id)
    if registration is not None:
        return {'code': 0, 'data': registration.config_store.value.model_dump(), 'message': 'ok'}
    raise HTTPException(status_code=404, detail=text('extensions.not_found', extension_id=extension_id))


@router.patch('/{extension_id}/config', summary='更新扩展配置')
async def patch_extension_config(extension_id: str, request: Request, user: dict = Depends(require_role(UserRole.admin))):
    """更新扩展配置，校验失败返回字段级错误且不修改原配置。"""
    patch_data = await parse_json_object(request)
    extension = extension_manager.registry.get(extension_id)
    if extension is not None:
        if not extension.is_bound:
            return {'code': 1, 'data': None, 'message': text('extensions.not_loaded')}
        try:
            extension.update_config(_restore_masked(extension.config.value.model_dump(), patch_data))
        except Exception as error:
            return {'code': 1, 'data': None, 'message': text('extensions.config_invalid', error=error)}
        return {'code': 0, 'data': None, 'message': 'ok'}
    registration = extension_manager.renderer_manager.templates.get(extension_id)
    if registration is not None:
        try:
            current = registration.config_store.value.model_dump(mode='json')
            registration.config_store.update(_restore_masked(current, patch_data))
        except Exception as error:
            return {'code': 1, 'data': None, 'message': text('extensions.config_invalid', error=error)}
        return {'code': 0, 'data': None, 'message': 'ok'}
    raise HTTPException(status_code=404, detail=text('extensions.not_found', extension_id=extension_id))


@router.delete('/{extension_id}', summary='卸载扩展')
async def uninstall_extension(extension_id: str, user: dict = Depends(require_role(UserRole.admin))):
    """提交扩展卸载任务（后台删除目录并同步依赖），进度在任务中心查看。"""
    _ensure_extension_exists(extension_id)
    name = extension_manager.get_extension_info(extension_id).get('name') or extension_id
    task = task_center.submit(
        TaskKind.extension_uninstall,
        lambda context: run_extension_uninstall_task(context, extension_id, name),
        title_params={'name': name},
    )
    return {'code': 0, 'data': task, 'message': text('task_center.submitted')}


@router.get('/renderers', summary='可用渲染引擎列表')
async def get_renderers(current_user: dict = Depends(get_current_user)):
    """返回全部渲染插件（含图片模式未开启而禁用的），标注可用性与当前选中。"""
    active_names = set(extension_manager.renderers)
    items = []
    for extension in extension_manager.registry.values():
        metadata = extension.metadata
        if ExtensionType.renderer not in metadata.types:
            continue
        name = metadata.renderer_name or metadata.id
        items.append(
            {
                'name': name,
                'current': name == config.image.renderer,
                'available': name in active_names,
                'state': extension.state.value,
                'reason': extension.failure_reason or None,
            }
        )
    items.sort(key=lambda item: (not item['available'], item['name']))
    return {'code': 0, 'data': items, 'message': 'ok'}


@router.get('/config-items', summary='全部扩展配置列表')
async def get_config_items(current_user: dict = Depends(get_current_user)):
    """返回全部可编辑扩展（代码扩展 + 无代码模板包）的配置 schema 与当前值，供配置中心统一编辑。"""
    items = []
    for extension in extension_manager.registry.values():
        # 未绑定扩展（禁用 / 阻塞的展示实例）无配置模型，无配置项可编辑
        if not extension.is_bound:
            continue
        schema = extension.get_config_schema()
        if not (schema or {}).get('properties'):
            continue
        metadata = extension.metadata
        items.append(
            {
                'id': metadata.id,
                'name': metadata.name,
                'description': metadata.description,
                'types': [entry.value for entry in metadata.types],
                'state': extension.state.value,
                'schema': schema,
                'values': _mask_config(extension),
            }
        )
    # 纯无代码模板包（混合扩展已在 registry 中展示，跳过避免同一 id 重复）
    for extension_id, registration in extension_manager.templates.items():
        if extension_id in extension_manager.registry:
            continue
        schema = registration.config_model.model_json_schema()
        if not (schema or {}).get('properties'):
            continue
        no_code = extension_manager.no_code_info.get(extension_id, {})
        items.append(
            {
                'id': extension_id,
                'name': no_code.get('name') or extension_id,
                'description': no_code.get('description') or '',
                'types': no_code.get('types') or [ExtensionType.template.value],
                'state': no_code.get('state') or ExtensionState.enabled.value,
                'schema': schema,
                'values': registration.config_store.value.model_dump(mode='json'),
            }
        )
    items.sort(key=lambda item: item['id'])
    return {'code': 0, 'data': items, 'message': 'ok'}


@router.get('/render-configs', summary='渲染插件配置列表')
async def get_render_configs(current_user: dict = Depends(get_current_user)):
    """返回所有渲染类扩展（渲染器 + 模板）的配置 schema 与当前值，供渲染设置页内联编辑。"""
    active_names = set(extension_manager.renderers)
    items = []
    # 渲染器类型扩展（含图片模式未开启而禁用的）
    for extension in extension_manager.registry.values():
        metadata = extension.metadata
        if ExtensionType.renderer not in metadata.types:
            continue
        name = metadata.renderer_name or metadata.id
        items.append(
            {
                'id': metadata.id,
                'kind': 'renderer',
                'name': metadata.name,
                'renderer_name': name,
                'current': name == config.image.renderer,
                'available': name in active_names,
                'state': extension.state.value,
                'reason': extension.failure_reason or None,
                # 未绑定扩展（图片模式未开启被禁用）无配置模型，schema 为空
                'schema': extension.get_config_schema() if extension.config_model is not None else None,
                'values': _mask_config(extension),
            }
        )
    # 模板类型扩展（纯无代码包 + 混合扩展的模板部分）
    for extension_id, registration in extension_manager.templates.items():
        # 混合扩展在 registry 中有实例，展示信息优先取实例
        registry_extension = extension_manager.registry.get(extension_id)
        no_code = extension_manager.no_code_info.get(extension_id, {})
        display_name = (registry_extension.metadata.name if registry_extension else '') or no_code.get('name')
        items.append(
            {
                'id': extension_id,
                'kind': 'template',
                'template_id': extension_id,
                'name': display_name or extension_id,
                'current': extension_id == config.image.template,
                'available': True,
                'state': registry_extension.state.value if registry_extension else 'enabled',
                'reason': registry_extension.failure_reason if registry_extension else None,
                'schema': registration.config_model.model_json_schema(),
                'values': registration.config_store.value.model_dump(mode='json'),
            }
        )
    items.sort(key=lambda item: (item['kind'] != 'renderer', not item['available'], item['id']))
    return {'code': 0, 'data': items, 'message': 'ok'}


@router.post('/renderers/switch', summary='切换渲染引擎')
async def switch_renderer(body: NameSwitchRequest, user: dict = Depends(require_role(UserRole.admin))):
    """切换渲染引擎并写回 Config.toml。"""
    name = body.name
    # 校验目标是「已安装的渲染器扩展」，而非「已启用/已 setup 的引擎实例」
    # （否则图片模式未开启或目标引擎尚未 setup 时会被误判为不存在）
    installed = {
        (ext.metadata.renderer_name or ext.metadata.id)
        for ext in extension_manager.registry.values()
        if ExtensionType.renderer in ext.metadata.types
    }
    if name not in installed:
        return {'code': 1, 'data': None, 'message': text('extensions.renderer_not_found', name=name)}
    _patch_image_config('renderer', name)
    return {'code': 0, 'data': None, 'message': 'ok'}


@router.get('/templates', summary='可用模板列表')
async def get_templates(current_user: dict = Depends(get_current_user)):
    """返回可用模板包列表（含当前选中）。"""
    templates = [
        {'name': template_id, 'current': template_id == config.image.template}
        for template_id in extension_manager.templates
    ]
    return {'code': 0, 'data': templates, 'message': 'ok'}


@router.post('/templates/switch', summary='切换模板')
async def switch_template(body: NameSwitchRequest, user: dict = Depends(require_role(UserRole.admin))):
    """切换模板包并立即使模板缓存失效。"""
    template_name = body.name
    if template_name not in extension_manager.templates:
        return {'code': 1, 'data': None, 'message': text('extensions.template_not_found', template_name=template_name)}
    _patch_image_config('template', template_name)
    # 标准用法：直接使全部模板环境失效
    extension_manager.renderer_manager.invalidate_all()
    return {'code': 0, 'data': None, 'message': 'ok'}


def _patch_image_config(field_name: str, value: str) -> None:
    """将 image.<field> 写入 Config.toml 并热更新内存配置。"""
    config_manager.update_config({'image': {field_name: value}})
    reload_config()
