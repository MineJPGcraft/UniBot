import asyncio
import re
from pathlib import Path

from Scripts.Logging import logger


class CacheManager:
    """缓存管理器，负责运行时缓存文件（如玩家头像）的读写与清理。"""

    # 缓存文件目录：保存渲染所需的运行时文件（如玩家头像）
    cache_dir = Path(__file__).parent.parent.parent / 'Data' / 'Avatars'

    def get_path(self, name: str) -> Path:
        """将名称解析为缓存目录中的文件路径（自动转为安全文件名，统一 .png 后缀）。"""
        return self.cache_dir / f'{self.sanitize_name(name)}.png'

    def get_cached(self, names: list[str]) -> tuple[dict[str, str], list[str]]:
        """检查本地缓存，返回 (已缓存的 {名称: 文件路径}, 缺失需下载的名称列表)。"""
        cached: dict[str, str] = {}
        missing: list[str] = []
        for name in names:
            avatar_path = self.get_path(name)
            if avatar_path.is_file():
                cached[name] = str(avatar_path)
                continue
            missing.append(name)
        return cached, missing

    async def save_all(self, files: dict[str, bytes]) -> dict[str, str]:
        """批量写入缓存文件，返回 {文件名: 文件完整路径}。"""
        if not files:
            return {}
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tasks = [asyncio.to_thread(self._write, name, content) for name, content in files.items()]
        paths = await asyncio.gather(*tasks)
        return dict(zip(files.keys(), paths))

    def sanitize_name(self, name: str) -> str:
        """将任意名称转为安全的文件名（仅保留字母数字与 _-）。"""
        return re.sub(r'[^0-9a-zA-Z_\-]', '_', name)

    def clear(self):
        """清理缓存目录中的所有文件。"""
        if not self.cache_dir.exists():
            return
        for file in self.cache_dir.iterdir():
            if file.is_file():
                file.unlink()
        logger.debug('Cache files cleaned up.')

    def _write(self, file_name: str, content: bytes) -> str:
        """将单个文件写入缓存目录，返回文件完整路径。"""
        file_path = self.cache_dir / file_name
        file_path.write_bytes(content)
        return str(file_path)


cache_manager = CacheManager()
