from pathlib import Path
from typing import Any

import tomlkit

from Scripts.Constants import MESSAGES_EN_PATH, MESSAGES_LEGACY_PATH, MESSAGES_ZH_PATH


class MessageGroup:
    """
    嵌套消息表，支持 messages.<表>.<子表>.<键> 链式访问消息文本
        占位符使用 Python str.format 语法，如 messages.xxx.yyy.format(player='Steve')。
    """

    __slots__ = ('_data',)

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            raise AttributeError(key)
        if key not in self._data:
            raise AttributeError(f'Message [{key}] is missing from the messages file!')
        value = self._data[key]
        if isinstance(value, dict):
            return MessageGroup(value)
        if isinstance(value, (str, list)):
            return value
        raise TypeError(f'[{key}] in the messages file should be a string or a list of strings!')


LANGUAGE_MESSAGE_FILES = {'zh': MESSAGES_ZH_PATH, 'en': MESSAGES_EN_PATH}

# 隐藏区块标记：两行注释之间的内容不对 WebUI 消息编辑器展示（机器人加载不受影响）
HIDDEN_START_MARKER = '# Hidden Start'
HIDDEN_END_MARKER = '# Hidden End'


def resolve_messages_path(language: str) -> Path:
    """解析语言对应的消息文件路径，旧版单文件仅作为中文包回退。"""
    if (path := LANGUAGE_MESSAGE_FILES.get(language)) and path.exists():
        return path
    if language == 'zh' and MESSAGES_LEGACY_PATH.exists():
        return MESSAGES_LEGACY_PATH
    expected_path = LANGUAGE_MESSAGE_FILES.get(language, MESSAGES_ZH_PATH)
    raise FileNotFoundError(
        f'Message config file for language [{language}] does not exist, '
        f'please create {expected_path} and fill in as needed!'
    )


def load_messages() -> MessageGroup:
    """按当前配置语言加载对应的消息包（zh / en），文件缺失则抛错。"""
    # 函数内导入：避免 Scripts.Messages 进入 Scripts.Config 的早期加载链（见 AGENT.md §0.13）
    from Scripts.Config import config

    toml_data = tomlkit.parse(resolve_messages_path(config.language).read_text('Utf-8'))
    return MessageGroup(dict(toml_data))


def reload_messages() -> None:
    """重新加载消息配置，供保存后热更新。"""

    global messages

    messages = load_messages()


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


messages = load_messages()
