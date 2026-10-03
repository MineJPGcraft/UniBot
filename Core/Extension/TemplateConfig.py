"""
模板受限配置 schema 编译（template 无代码扩展专用）。

把清单 `[template].config_schema` 声明编译为受限 Pydantic 模型：字段名必须是
合法标识符，类型仅限 `string/integer/number/boolean/color/select`，约束与类型
不匹配、select 缺选项或默认值不在选项中等情况一律阻止注册。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from .Errors import ExtensionError
from .Manifest import TemplateFieldConfig

# 受限配置字段名：合法 Python 标识符且不以 _ 开头
_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# 颜色：#RRGGBB 或 #RRGGBBAA
_COLOR_RE = re.compile(r'^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')


def build_template_config_model(
    extension_id: str,
    schema: dict[str, TemplateFieldConfig],
) -> type[BaseModel]:
    """
    把清单受限 config_schema 编译为 Pydantic 模型。

        字段名必须为合法 Python 标识符且不以 `_` 开头；每项必须提供类型与
        默认值。类型仅限 `string/integer/number/boolean/color/select`，约束
        与类型不匹配、select 缺选项或默认值不在选项中等情况一律阻止注册。
    """
    fields: dict[str, tuple[Any, Any]] = {}
    for field_name, field_cfg in schema.items():
        if not _IDENTIFIER_RE.match(field_name) or field_name.startswith('_'):
            raise ExtensionError(
                f'template {extension_id} 配置字段名非法：{field_name}！字段名必须是合法 Python 标识符且不能以下划线开头！'
            )
        fields[field_name] = _map_template_field(extension_id, field_name, field_cfg)
    return create_model(
        f'TemplateConfig_{extension_id}',
        __config__=ConfigDict(extra='forbid'),
        **fields,  # type: ignore[arg-type]
    )


def _reject_misplaced_constraints(
    cfg: TemplateFieldConfig,
    reject: Callable[[str], ExtensionError],
    *,
    allow_min_max: bool = False,
    allow_length: bool = False,
    allow_options: bool = False,
) -> None:
    """校验约束字段与当前类型匹配，错位约束（如数值字段的 options）一律拒绝。"""
    if not allow_min_max and (cfg.min is not None or cfg.max is not None):
        raise reject('min/max only apply to integer/number')
    if not allow_length and (cfg.min_length is not None or cfg.max_length is not None):
        raise reject('min_length/max_length only apply to string')
    if not allow_options and cfg.options:
        raise reject('options only apply to select')


def _map_template_field(
    extension_id: str,
    field_name: str,
    cfg: TemplateFieldConfig,
) -> tuple[Any, Any]:
    """按类型映射为 Pydantic 字段，并校验约束与默认值合法性。"""
    reject = _template_field_rejector(extension_id, field_name)
    default = cfg.default
    field_kwargs = _template_field_kwargs(cfg)

    # 保留 title/description；color 编译为 str 后原始类型会丢失，
    # 因此按统一契约补 `format: 'color'`（与 Config.toml / .env 的 Schema 一致）。
    # select 编译为 Literal 自带 enum，无需额外标记。
    if cfg.type in ('integer', 'number'):
        return _build_number_field(cfg, default, field_kwargs, reject)
    if cfg.type == 'string':
        return _build_string_field(cfg, default, field_kwargs, reject)
    if cfg.type == 'boolean':
        return _build_boolean_field(cfg, default, field_kwargs, reject)
    if cfg.type == 'color':
        return _build_color_field(cfg, default, field_kwargs, reject)
    return _build_select_field(cfg, default, field_kwargs, reject)


def _template_field_rejector(extension_id: str, field_name: str) -> Callable[[str], ExtensionError]:
    """构造带上下文的字段校验拒绝器。"""

    def reject(reason: str) -> ExtensionError:
        return ExtensionError(f'template {extension_id} config field {field_name} {reason}')

    return reject


def _template_field_kwargs(cfg: TemplateFieldConfig) -> dict[str, Any]:
    """构造所有字段通用的 title/description/color 标记。"""
    field_kwargs: dict[str, Any] = {}
    if cfg.type == 'color':
        field_kwargs['json_schema_extra'] = {'format': 'color'}
    if cfg.title:
        field_kwargs['title'] = cfg.title
    if cfg.description:
        field_kwargs['description'] = cfg.description
    return field_kwargs


def _typed_number_constraint(
    cfg: TemplateFieldConfig, target: type, reject: Callable[[str], ExtensionError]
) -> dict[str, Any]:
    """构造数值范围约束，min/max 类型不符时拒绝。"""
    constraints: dict[str, Any] = {}
    if cfg.min is not None:
        if not isinstance(cfg.min, target) or isinstance(cfg.min, bool):
            raise reject(f'min must be of type {target.__name__}')
        constraints['ge'] = cfg.min
    if cfg.max is not None:
        if not isinstance(cfg.max, target) or isinstance(cfg.max, bool):
            raise reject(f'max must be of type {target.__name__}')
        constraints['le'] = cfg.max
    return constraints


def _length_constraints(cfg: TemplateFieldConfig, reject: Callable[[str], ExtensionError]) -> dict[str, Any]:
    """构造字符串长度约束，取值非法时拒绝。"""
    constraints: dict[str, Any] = {}
    for attr, key in (('min_length', 'min_length'), ('max_length', 'max_length')):
        value = getattr(cfg, attr)
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise reject(f'{attr} must be a non-negative integer')
        constraints[key] = value
    return constraints


def _build_number_field(
    cfg: TemplateFieldConfig, default: Any, field_kwargs: dict[str, Any], reject: Callable[[str], ExtensionError]
) -> tuple[Any, Any]:
    """构造 integer/number 字段。"""
    target = int if cfg.type == 'integer' else float
    if not isinstance(default, target) or isinstance(default, bool):
        raise reject(f'default must be of type {target.__name__}')
    _reject_misplaced_constraints(cfg, reject, allow_min_max=True)
    return (target, Field(default=default, **_typed_number_constraint(cfg, target, reject), **field_kwargs))


def _build_string_field(
    cfg: TemplateFieldConfig, default: Any, field_kwargs: dict[str, Any], reject: Callable[[str], ExtensionError]
) -> tuple[Any, Any]:
    """构造 string 字段。"""
    if not isinstance(default, str):
        raise reject('default must be a string')
    _reject_misplaced_constraints(cfg, reject, allow_length=True)
    return (str, Field(default=default, **_length_constraints(cfg, reject), **field_kwargs))


def _build_boolean_field(
    cfg: TemplateFieldConfig, default: Any, field_kwargs: dict[str, Any], reject: Callable[[str], ExtensionError]
) -> tuple[Any, Any]:
    """构造 boolean 字段。"""
    if not isinstance(default, bool):
        raise reject('default must be a boolean')
    _reject_misplaced_constraints(cfg, reject)
    return (bool, Field(default=default, **field_kwargs))


def _build_color_field(
    cfg: TemplateFieldConfig, default: Any, field_kwargs: dict[str, Any], reject: Callable[[str], ExtensionError]
) -> tuple[Any, Any]:
    """构造 color 字段（#RRGGBB 或 #RRGGBBAA）。"""
    if not isinstance(default, str) or not _COLOR_RE.match(default):
        raise reject('default must be a #RRGGBB or #RRGGBBAA color')
    _reject_misplaced_constraints(cfg, reject)
    return (str, Field(default=default, **field_kwargs))


def _build_select_field(
    cfg: TemplateFieldConfig, default: Any, field_kwargs: dict[str, Any], reject: Callable[[str], ExtensionError]
) -> tuple[Any, Any]:
    """构造 select 字段（Literal + 选项校验）。"""
    if not cfg.options:
        raise reject('select type requires non-empty options')
    if default not in cfg.options:
        raise reject('default must be one of the options')
    _reject_misplaced_constraints(cfg, reject)
    return (Literal[tuple(cfg.options)], Field(default=default, **field_kwargs))
