"""
配置相关的 FastAPI 路由。

负责 `Config.toml`、`.env`、`pyproject.toml`（NoneBot 适配器/插件）的读写接口。
"""

from copy import deepcopy

from fastapi import APIRouter, Depends, Request

from Scripts.Api.Locale import text
from Scripts.Config import CONFIG_TOML_PATH, Config, config, reload_config, validate_config_content
from Scripts.Constants import BUILTIN_PLUGIN_PREFIX
from Scripts.Managers import config_manager

from ..Auth import get_current_user, require_role
from ..Body import parse_json_object
from ..Schemas import (
    InstallAdapterRequest,
    MessagesPatchRequest,
    NoneBotItemRequest,
    RawConfigPatchRequest,
    UninstallAdapterRequest,
)
from .Adapters import ADAPTER_CATALOG, PROTECTED_ADAPTER_MODULES
from .Driver import compute_redundant_drivers, format_driver, merge_driver, shrink_driver
from .Helpers import deep_merge, sanitize_none
from .Schema import build_config_groups, build_config_schema, build_env_groups, build_env_schema

router = APIRouter(prefix='/api/config', tags=['Config'])

# tomlkit 不支持 None 值，写盘前替换为空字符串
# NoneBot 内置配置字段（port/superusers/command_start）在 .env 中管理，不写入 Config.toml
_TOML_SKIP_KEYS = ('port', 'superusers', 'command_start')


def _localized_adapter(adapter: dict) -> dict:
    """返回注入了请求语言译名的适配器目录条目副本（注册等逻辑仍使用原始数据）。"""
    adapter_slug = adapter['id'].replace('-', '_').replace(' ', '_').lower()
    return {
        **adapter,
        'name': text(f'adapters.catalog.{adapter_slug}_name'),
        'description': text(f'adapters.catalog.{adapter_slug}_description'),
    }


def _apply_language_change(previous_language: str) -> str | None:
    """
    机器人消息语言变更后重载消息包（与 WebUI 界面语言无关）。
    新语言包缺失时回退旧语言（含写回磁盘），返回错误提示；无需处理返回 None。
    """
    if config.language == previous_language:
        return None
    try:
        # 函数内导入：Scripts.Messages 顶层会触发 Scripts.Config 加载，避免进入早期导入链
        from Scripts.Messages import reload_messages

        reload_messages()
    except FileNotFoundError as error:
        config.language = previous_language
        config_manager.update_config({'language': previous_language})
        return str(error)
    return None


@router.get('', summary='获取配置')
async def get_config(current_user: dict = Depends(get_current_user)):
    """获取完整配置。"""
    return {
        'code': 0,
        'data': config.model_dump(),
        'message': 'ok',
    }


@router.get('/schema', summary='获取配置 Schema')
async def get_config_schema(current_user: dict = Depends(get_current_user)):
    """获取配置的 JSON Schema，供前端动态渲染表单。"""
    return {
        'code': 0,
        'data': {
            'fields': build_config_schema(),
            'groups': build_config_groups(),
        },
        'message': 'ok',
    }


@router.patch('', summary='更新配置')
async def patch_config(request: Request, current_user: dict = Depends(require_role('admin'))):
    """部分更新配置，深合并后写回 Config.toml 并热更新。"""
    patch_data = await parse_json_object(request)
    previous_language = config.language

    merged_data = deep_merge(config.model_dump(), patch_data)
    toml_output = deepcopy(merged_data)
    for key in _TOML_SKIP_KEYS:
        toml_output.pop(key, None)

    try:
        config_manager.update_config(sanitize_none(toml_output))
    except Exception as error:
        return {'code': 1, 'data': None, 'message': text('config.write.failed', error=error)}

    # 热更新内存中的配置对象（先经模型校验，保证嵌套配置仍为 Pydantic 子模型而非 dict）
    updated_config = Config.model_validate(merged_data)
    for field_name in Config.model_fields:
        setattr(config, field_name, getattr(updated_config, field_name))

    if error_message := _apply_language_change(previous_language):
        return {'code': 1, 'data': None, 'message': error_message}
    return {'code': 0, 'data': None, 'message': 'ok'}


# ===== Messages.toml 消息文本 =====


@router.get('/messages', summary='获取消息文本配置')
async def get_messages(current_user: dict = Depends(get_current_user)):
    """获取 Messages.toml 的原始文本内容。"""
    return {
        'code': 0,
        'data': {
            'messages_toml': config_manager.read_messages_raw(),
        },
        'message': 'ok',
    }


@router.patch('/messages', summary='保存消息文本配置')
async def patch_messages(body: MessagesPatchRequest, current_user: dict = Depends(require_role('admin'))):
    """以原始文本方式保存 Messages.toml 并热更新。"""
    try:
        config_manager.write_messages_raw(body.messages_toml)
    except Exception as error:
        return {'code': 1, 'data': None, 'message': text('config.messages.write_failed', error=error)}
    return {'code': 0, 'data': None, 'message': text('config.messages.saved')}


# ===== .env 环境变量配置 =====


@router.get('/env', summary='获取环境变量配置')
async def get_env_config(current_user: dict = Depends(get_current_user)):
    """获取 .env 中的配置项。"""
    return {
        'code': 0,
        'data': {
            'values': config_manager.read_env(),
            'schema': build_env_schema(),
            'groups': build_env_groups(),
        },
        'message': 'ok',
    }


@router.patch('/env', summary='更新环境变量配置')
async def patch_env_config(request: Request, current_user: dict = Depends(require_role('admin'))):
    """部分更新 .env 配置，写回文件（需重启生效）。"""
    patch_data = await parse_json_object(request)
    config_manager.update_env(patch_data)
    return {'code': 0, 'data': None, 'message': text('config.ok.restart_required')}


# ===== 原始文件直接编辑 =====


@router.get('/raw', summary='获取原始配置文件内容')
async def get_raw_config(current_user: dict = Depends(get_current_user)):
    """获取 Config.toml 与 .env 的原始文本内容。"""
    return {
        'code': 0,
        'data': {
            'config_toml': CONFIG_TOML_PATH.read_text('Utf-8'),
            'env': config_manager.env_path.read_text('Utf-8'),
        },
        'message': 'ok',
    }


@router.patch('/raw', summary='保存原始配置文件内容')
async def patch_raw_config(body: RawConfigPatchRequest, current_user: dict = Depends(require_role('admin'))):
    """以原始文本方式保存 Config.toml / .env（.env 改动需重启生效）。"""
    hints = []
    previous_language = config.language
    if body.config_toml is not None:
        if error_message := validate_config_content(body.config_toml):
            return {'code': 1, 'data': None, 'message': error_message}
        CONFIG_TOML_PATH.write_text(body.config_toml, encoding='Utf-8')
        reload_config()
        if error_message := _apply_language_change(previous_language):
            return {'code': 1, 'data': None, 'message': error_message}
        hints.append(text('config.hint.config_toml_reloaded'))

    if body.env is not None:
        config_manager.write_env_raw(body.env)
        hints.append(text('config.hint.env_saved'))

    if not hints:
        return {'code': 1, 'data': None, 'message': text('config.nothing.to_save')}
    return {'code': 0, 'data': None, 'message': text('config.hint.separator').join(hints)}


# ===== pyproject.toml NoneBot 插件/适配器管理 =====


@router.get('/nonebot', summary='获取 NoneBot 插件与适配器列表')
async def get_nonebot_config(current_user: dict = Depends(get_current_user)):
    """获取 pyproject.toml 中的 NoneBot 适配器和插件配置。"""
    project_data = config_manager.read_pyproject()
    nonebot_section = project_data.get('tool', {}).get('nonebot', {})
    adapters = [
        {**adapter, 'removable': adapter.get('module_name') not in PROTECTED_ADAPTER_MODULES}
        for adapter in nonebot_section.get('adapters', [])
        if isinstance(adapter, dict)
    ]
    registered_modules = {adapter.get('module_name') for adapter in adapters}
    installed_packages = config_manager.get_dependency_packages()
    catalog = [
        {
            **_localized_adapter(adapter),
            'registered': adapter['module_name'] in registered_modules,
            'installed': adapter['package'] in installed_packages,
            'removable': adapter['module_name'] not in PROTECTED_ADAPTER_MODULES,
        }
        for adapter in ADAPTER_CATALOG
    ]
    return {
        'code': 0,
        'data': {
            'adapters': adapters,
            'plugins': nonebot_section.get('plugins', []),
            'adapter_catalog': catalog,
        },
        'message': 'ok',
    }


@router.post('/nonebot/adapters/install', summary='安装并注册适配器')
async def install_adapter(body: InstallAdapterRequest, current_user: dict = Depends(require_role('admin'))):
    """向 pyproject.toml 写入依赖记录和 NoneBot 适配器配置，并自动补全所需驱动。"""
    adapter = next((item for item in ADAPTER_CATALOG if item['id'] == body.adapter_id), None)
    if adapter is None:
        return {'code': 1, 'data': None, 'message': text('config.adapter.not_found')}
    config_manager.add_dependency(adapter['package'])
    config_manager.add_adapter(adapter['name'], adapter['module_name'])
    new_driver, added_drivers = merge_driver(adapter.get('drivers', []))
    message = text('config.adapter.install_success')
    if added_drivers:
        message += text('config.adapter.install_drivers_added', drivers=format_driver(added_drivers), driver=new_driver)
    return {'code': 0, 'data': _localized_adapter(adapter), 'message': message}


@router.post('/nonebot/adapters', summary='添加适配器')
async def add_adapter(body: NoneBotItemRequest, current_user: dict = Depends(require_role('admin'))):
    """向 pyproject.toml 添加适配器。"""
    if config_manager.add_adapter(body.name, body.module_name):
        return {'code': 0, 'data': None, 'message': text('config.ok.restart_required')}
    return {'code': 1, 'data': None, 'message': text('config.adapter.already_exists')}


@router.delete('/nonebot/adapters', summary='移除适配器注册')
async def remove_adapter(body: NoneBotItemRequest, current_user: dict = Depends(require_role('admin'))):
    """从 pyproject.toml 移除适配器注册（不删除依赖包）。"""
    if body.module_name in PROTECTED_ADAPTER_MODULES:
        return {'code': 1, 'data': None, 'message': text('config.adapter.protected')}
    config_manager.remove_adapter(body.module_name)
    return {'code': 0, 'data': None, 'message': text('config.adapter.disabled')}


@router.delete('/nonebot/adapters/uninstall', summary='彻底卸载适配器')
async def uninstall_adapter(body: UninstallAdapterRequest, current_user: dict = Depends(require_role('admin'))):
    """从 pyproject.toml 移除适配器注册和依赖记录，并清理多余驱动。"""
    if body.module_name in PROTECTED_ADAPTER_MODULES:
        return {'code': 1, 'data': None, 'message': text('config.adapter.protected')}
    adapter = next(
        (item for item in ADAPTER_CATALOG if item['module_name'] == body.module_name),
        None,
    )
    if adapter is None:
        return {'code': 1, 'data': None, 'message': text('config.adapter.uninstall_not_found')}
    config_manager.remove_adapter(body.module_name)
    config_manager.remove_dependency(adapter['package'])
    redundant = compute_redundant_drivers(body.module_name)
    new_driver, removed_drivers = shrink_driver(redundant)
    message = text('config.adapter.uninstall_success')
    if removed_drivers:
        message += text(
            'config.adapter.uninstall_drivers_removed', drivers=format_driver(removed_drivers), driver=new_driver
        )
    return {'code': 0, 'data': None, 'message': message}


@router.post('/nonebot/plugins', summary='添加插件')
async def add_plugin(body: NoneBotItemRequest, current_user: dict = Depends(require_role('admin'))):
    """向 pyproject.toml 添加插件。"""
    if config_manager.add_plugin(body.module_name):
        return {'code': 0, 'data': None, 'message': text('config.ok.restart_required')}
    return {'code': 1, 'data': None, 'message': text('config.plugin.already_exists')}


@router.delete('/nonebot/plugins', summary='移除插件')
async def remove_plugin(body: NoneBotItemRequest, current_user: dict = Depends(require_role('admin'))):
    """从 pyproject.toml 移除插件。"""
    if body.module_name.startswith(BUILTIN_PLUGIN_PREFIX):
        return {'code': 1, 'data': None, 'message': text('config.plugin.builtin_protected')}
    config_manager.remove_plugin(body.module_name)
    return {'code': 0, 'data': None, 'message': text('config.ok.restart_required')}
