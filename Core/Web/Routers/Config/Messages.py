"""
消息文本编辑器后端：按翻译键的**命名空间**构建嵌套树、下发默认/生效值与占位符、保存覆盖层。

用户覆盖层文件为 `Config/Messages.{zh,en}.toml`，**仅保存用户改过的键**。
可覆盖性按**文件来源**判定：系统键（由 `Core/Locales/System.*.toml` 提供——系统指令 `/bot`、
内置扩展/插件名称、面板界面 `api.*`）受保护且不下发；`Core/Locales/Messages.*.toml` 与扩展
语言包提供的键（事件播报、其余指令、扩展消息 `ext.*`）可被用户覆盖。

`build_message_tree()` 把生效目录按键路径（如 `core.commands.luck.result`）拆成**命名空间树**：
每个中间节点是命名空间（`core` → `commands` → `luck`），叶子节点挂具体消息项。每项的 `value`
为**生效值**（用户改过则为其覆盖值，否则为默认译文），`base_value` 为默认译文，两者不同即标记
已修改。前端渲染为可展开/折叠的树；`save_overrides()` 会剔除受保护键与未改动项后写盘。
"""

from __future__ import annotations

from typing import Any

from Core.I18n import i18n
from Core.I18n.Engine import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from Core.I18n.Loader import write_override

from ...Locale import text

# 命名空间段 → 界面标签键（仅对常见的顶层/二层命名空间提供友好译名，其余回退原始段名）。
_NAMESPACE_LABELS: dict[str, str] = {
    'core': 'messages.group_core',
    'commands': 'messages.group_commands',
    'events': 'messages.group_events',
    'ext': 'messages.group_extensions',
}


def _resolve_language(language: str | None) -> str:
    """校验语言参数，非法回退默认语言。"""
    if language in SUPPORTED_LANGUAGES:
        return language
    return DEFAULT_LANGUAGE


def _namespace_label(segment: str) -> str:
    """命名空间段的展示标签：有译名用译名，否则原样返回段名（如扩展 ID）。"""
    label_key = _NAMESPACE_LABELS.get(segment)
    return text(label_key) if label_key else segment


def _build_item(language: str, key: str) -> dict[str, Any]:
    """构建单个键的展示项：生效值、默认值、是否已改、列表标记与占位符。"""
    value = i18n.raw_value(language, key)
    base_value = i18n.base_value(language, key)
    is_list = isinstance(value, list)
    placeholders = i18n.find_placeholders(value) if isinstance(value, str) else []
    return {
        'key': key,
        'path': key.split('.'),
        'value': value,
        'base_value': base_value,
        'modified': value != base_value,
        'is_list': is_list,
        'placeholders': placeholders,
    }


def _new_namespace(segment: str, path: str) -> dict[str, Any]:
    """新建一个命名空间节点（子节点与叶子项均按需挂载）。"""
    return {
        'name': segment,
        'path': path,
        'label': _namespace_label(segment),
        'children': {},
        'items': [],
    }


def _build_tree(language: str) -> tuple[dict[str, Any], int, int]:
    """
    把生效目录按键路径折叠为命名空间树。

    返回 `(根节点, 叶子总数, 已修改数)`；受保护键与不可编辑值（非 str / 全字符串列表）被跳过。
    """
    root = _new_namespace('', '')
    total = 0
    modified = 0
    for key in sorted(i18n.catalog_keys(language)):
        if i18n.is_protected(key):
            continue
        item = _build_item(language, key)
        if not isinstance(item['value'], (str, list)):
            continue
        segments = key.split('.')
        node = root
        for depth, segment in enumerate(segments[:-1]):
            node = node['children'].setdefault(
                segment, _new_namespace(segment, '.'.join(segments[: depth + 1]))
            )
        node['items'].append(item)
        total += 1
        modified += int(item['modified'])
    return root, total, modified


def _serialize_node(node: dict[str, Any]) -> dict[str, Any]:
    """把内部命名空间节点序列化为前端可消费的 JSON（递归，含子树计数）。"""
    children = [_serialize_node(child) for child in node['children'].values()]
    children.sort(key=lambda child: child['name'])
    items = node['items']
    return {
        'name': node['name'],
        'path': node['path'],
        'label': node['label'],
        'count': len(items) + sum(child['count'] for child in children),
        'modified_count': sum(int(item['modified']) for item in items)
        + sum(child['modified_count'] for child in children),
        'children': children,
        'items': items,
    }


def build_message_tree(language: str | None = None) -> dict[str, Any]:
    """构建某语言的消息**命名空间树**（含子树计数与已修改统计）。

    受保护键（系统指令与内置扩展/插件名称）用户不可修改，**不下发给前端**，避免造成误解。
    """
    resolved = _resolve_language(language)
    root, total, modified = _build_tree(resolved)
    tree = [_serialize_node(child) for child in root['children'].values()]
    tree.sort(key=lambda node: node['name'])
    return {
        'language': resolved,
        'tree': tree,
        'total_count': total,
        'modified_count': modified,
    }


def save_overrides(language: str | None, overrides: dict[str, Any]) -> int:
    """
    保存用户改动到覆盖层并热重载。

    `overrides` 为「点路径 → 新值」映射；受保护键与等于默认译文的项会被剔除，
    因此文件只保留用户真正改动过的键。返回实际写入的键数量。
    """
    resolved = _resolve_language(language)
    changed = _prune_unchanged(resolved, overrides)
    write_override(resolved, _assign_nested(changed))
    return len(changed)


def _prune_unchanged(language: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """剔除受保护键与等于默认译文的项，仅保留真正的用户改动。"""
    result: dict[str, Any] = {}
    for key, value in overrides.items():
        if i18n.is_protected(key):
            continue
        base_value = i18n.base_value(language, key)
        if base_value is None:
            continue
        if value == base_value:
            continue
        result[key] = value
    return result


def _assign_nested(flat: dict[str, Any]) -> dict[str, Any]:
    """把「点路径 → 值」映射还原为嵌套字典（供 TOML 写盘）。"""
    nested: dict[str, Any] = {}
    for key, value in flat.items():
        node = nested
        parts = key.split('.')
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return nested
