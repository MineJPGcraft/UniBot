"""
消息文本兼容薄层：把旧 `messages.<域>.<键>` 访问映射到统一 I18n 引擎。

内置命令等现有代码可用旧写法 `messages.commands.bot.description` **零改动**跑通，
底层解析到 `text('core.commands.bot.description')`。新代码请直接 `from Core.I18n import text`。

映射规则（`_legacy_map`）：
- `core.<rest>`            → 旧写法 `<rest>`（如 `core.events.player_join` → `events.player_join`）
- `builtin.<id>.<rest>`    → 旧写法 `plugins.<id>.<rest>`（内置插件文案）
- `builtin.<id>.name`      → 旧写法 `builtin_extensions.<id>`（内置扩展展示名）

隐藏块工具（`strip_hidden_content` / `restore_hidden_content`）为纯字符串工具，保留备用。
"""

from Core.I18n import i18n
from Core.I18n.Context import get_locale
from Core.LocaleLoader import register_all

# 隐藏区块标记（通用字符串工具沿用）
HIDDEN_START_MARKER = '# Hidden Start'
HIDDEN_END_MARKER = '# Hidden End'


def _legacy_map() -> dict[str, str]:
    """构建「旧点路径 → 新命名空间键」映射。"""
    mapping: dict[str, str] = {}
    for key in i18n.available_keys():
        if key.startswith('core.'):
            mapping[key[len('core.'):]] = key
        elif key.startswith('builtin.'):
            rest = key[len('builtin.'):]
            mapping[f'plugins.{rest}'] = key
            if rest.endswith('.name'):
                mapping[f'builtin_extensions.{rest[:-len(".name")]}'] = key
    return mapping


class _LegacyGroup:
    """旧式消息对象：把属性链惰性解析为 I18n 点路径取值。"""

    __slots__ = ('_prefix',)

    def __init__(self, prefix: str = '') -> None:
        object.__setattr__(self, '_prefix', prefix)

    def __getattr__(self, key: str):
        if key.startswith('_'):
            raise AttributeError(key)
        prefix = object.__getattribute__(self, '_prefix')
        path = f'{prefix}.{key}' if prefix else key
        mapping = _legacy_map()
        if any(candidate.startswith(f'{path}.') for candidate in mapping):
            return _LegacyGroup(path)
        if path in mapping:
            return i18n.render_value(mapping[path], locale=get_locale())
        raise AttributeError(f'Message [{path}] is missing from the messages file!')


# 兼容实例：现有代码 `from Core.Messages import messages`
messages = _LegacyGroup()


def reload_messages() -> None:
    """重新加载语言包，供语言切换/保存覆盖层后热更新。"""
    register_all()


def _split_hidden_blocks(lines: list[str]) -> tuple[list[str], list[tuple[str | None, list[str]]]]:
    """
    分离隐藏块与可见行：每对 Hidden 标记连同内部内容整体从可见输出中移除。
    每个块记录「锚点」= 紧邻其起始标记之前最近的一行可见文本（用于保存时回插原位）；
    块位于文件开头时锚点为 None。未闭合的起始标记视为延伸到文件末尾。
    返回 (纯可见行列表, [(锚点行或 None, 块内容行列表)])。
    """
    visible: list[str] = []
    blocks: list[tuple[str | None, list[str]]] = []
    current_lines: list[str] | None = None
    current_anchor: str | None = None
    for line in lines:
        stripped = line.strip()
        if current_lines is None:
            if stripped == HIDDEN_START_MARKER:
                current_anchor = visible[-1] if visible else None
                current_lines = []
            else:
                visible.append(line)
        elif stripped == HIDDEN_END_MARKER:
            blocks.append((current_anchor, current_lines))
            current_lines = None
        else:
            current_lines.append(line)
    if current_lines is not None:
        blocks.append((current_anchor, current_lines))
    return visible, blocks


def _wrap_hidden_block(content: list[str]) -> list[str]:
    """把隐藏块内容包上完整标记对，作为写盘行序列。"""
    return [HIDDEN_START_MARKER, *content, HIDDEN_END_MARKER]


def strip_hidden_content(content: str) -> str:
    """移除全部隐藏块（含标记行本身），供 WebUI 消息编辑器展示。"""
    visible, _ = _split_hidden_blocks(content.splitlines())
    return '\n'.join(visible) + ('\n' if visible else '')


def restore_hidden_content(incoming: str, disk_content: str) -> str:
    """
    把磁盘文件中的隐藏块合并回 WebUI 提交的文本，返回最终写盘内容。
    回插位置按各块的锚点行（块前最近可见行）在提交文本中定位，保持原相对顺序；
    提交文本中出现的 Hidden 标记及其夹带内容视为无效输入整体丢弃；
    锚点行不存在（被编辑或删除）的块以完整标记对追加到文件末尾，保证数据不丢。
    """
    _, disk_blocks = _split_hidden_blocks(disk_content.splitlines())
    out_lines: list[str] = []
    pending = list(disk_blocks)
    inside_submitted_hidden = False
    for line in incoming.splitlines():
        stripped = line.strip()
        if inside_submitted_hidden:
            # 提交文本的隐藏区内部内容来源不可信，整体丢弃
            if stripped == HIDDEN_END_MARKER:
                inside_submitted_hidden = False
            continue
        if stripped == HIDDEN_START_MARKER:
            inside_submitted_hidden = True
            continue
        out_lines.append(line)
        while pending and pending[0][0] is not None and pending[0][0] == line:
            _, block_lines = pending.pop(0)
            out_lines.extend(_wrap_hidden_block(block_lines))

    # 无锚点（原位于文件开头）的块放回最前，其余按序追加到末尾
    head_lines: list[str] = []
    tail_lines: list[str] = []
    for anchor, block_lines in pending:
        (head_lines if anchor is None else tail_lines).extend(_wrap_hidden_block(block_lines))

    result_lines = head_lines + out_lines + tail_lines
    return '\n'.join(result_lines) + ('\n' if result_lines else '')


messages = _LegacyGroup()
