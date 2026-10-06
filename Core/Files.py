"""
文件写入工具：系统临时文件 + 原子替换（跨盘自动回退复制）。

统一收口项目内多处「先写临时文件再替换」的实现，避免进程中断留下截断文件；
仅依赖标准库，可在插件加载前的早期链路安全导入。

写盘策略：
- 临时文件写在**系统临时目录**（`tempfile` 默认位置），不污染目标文件所在目录；
- 优先用 `os.replace` 原子替换：同卷/同驱动器时原子且跨平台可靠；
- 若系统临时目录与目标**不在同一卷**（如 Windows 下 C: 与 D: 分属两盘、Linux 下
  `/tmp` 为 tmpfs），`os.replace` 无法跨盘移动，此时回退到 `shutil.move`
  （内部检测到重命名失败会自动改用「复制 + 删除」完成跨盘落地）。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

__all__ = ['atomic_write']


def atomic_write(file_path: Path, content: str | bytes) -> None:
    """
    以「临时文件 + 原子替换」写入文件，失败时保留旧文件。

        临时文件写在系统临时目录；先尝试 `os.replace` 原子替换，跨盘失败时回退
        `shutil.move`（复制 + 删除）。父目录不存在时自动创建；写入或替换失败时尽力
        清理临时文件并向上抛出原异常，由调用方决定如何记录/包装错误。
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    is_binary = isinstance(content, bytes)
    mode = 'wb' if is_binary else 'w'
    encoding = None if is_binary else 'Utf-8'
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode, encoding=encoding, suffix='.tmp', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
        try:
            os.replace(temp_path, file_path)
        except OSError:
            # 系统临时目录与目标可能不在同一卷/驱动器：os.replace 无法跨盘原子移动，
            # 退回 shutil.move（重命名失败时自动改为「复制 + 删除」）
            shutil.move(str(temp_path), str(file_path))
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
