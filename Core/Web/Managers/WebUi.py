import asyncio
import shutil
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from Core.Files import atomic_write
from Core.Logging import exception_logger, logger
from Core.Managers import config_manager
from Core.Network import github_download
from Core.Web.Locale import get_language, text

assets_missing_template = """
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: linear-gradient(135deg, #1f2937, #111827);
    color: #f9fafb;
  }}
  .card {{
    max-width: 480px;
    margin: 24px;
    padding: 40px 36px;
    text-align: center;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
  }}
  .icon {{ font-size: 56px; }}
  h1 {{ margin: 16px 0 12px; font-size: 22px; }}
  p {{ font-size: 15px; line-height: 1.8; color: #d1d5db; }}
</style>
</head>
<body>
<div class="card">
  <div class="icon">⚠️</div>
  <h1>{title}</h1>
  <p>{message}<br>{retry}</p>
</div>
</body>
</html>
"""


class WebUiManager:
    """WebUI 管理面板：负责 API 路由挂载、前端静态资源的版本校验/下载与静态文件挂载。"""

    app: FastAPI | None = None

    webui_dir: Path = Path('WebUi')
    version_file: Path = Path('WebUi/.version')

    @property
    def version(self) -> str:
        """当前期望的 WebUI 版本（来自 pyproject.toml [unibot] webui_version）。"""
        return config_manager.webui_version

    def read_local_version(self) -> str:
        """读取本地已下载的 WebUI 版本。"""
        if self.version_file.exists():
            return self.version_file.read_text('Utf-8').strip()
        return ''

    def is_ready(self) -> bool:
        """检查本地 WebUI 是否已下载且版本匹配。"""
        return (self.webui_dir / 'index.html').exists() and self.read_local_version() == self.version

    async def ensure_downloaded(self) -> bool:
        """确保 WebUI 静态资源已下载且版本匹配，否则重新下载。"""
        if not self.version:
            logger.warning('No WebUI version configured, skipping download.')
            return False
        if self.is_ready():
            logger.info(f'WebUI static assets ready ({self.version}).')
            return True
        logger.info(f'Downloading WebUI static assets ({self.version})...')
        url = f'https://github.com/MineJPGcraft/UniBot.WebUi/releases/download/{self.version}/WebUi.zip'
        if not (response := await github_download(url)):
            logger.warning(f'Failed to download WebUI ({self.version}), check your network and retry later.')
            return False
        try:
            # 解压与目录替换属于重 IO，放入线程执行避免阻塞事件循环
            await asyncio.to_thread(self._install_assets, response.getvalue())
            atomic_write(self.version_file, self.version)
        except Exception as error:
            logger.warning(f'Failed to extract WebUI static assets: {error}')
            return False
        logger.success(f'WebUI static assets downloaded ({self.version}).')
        return True

    def _install_assets(self, archive_data: bytes) -> None:
        """先解压到同目录 staging，再原子替换 WebUi 目录，失败时回滚旧版本（同步阻塞）。"""
        # 函数内导入：同 ensure_downloaded 的延迟导入原因（避免抢先注册插件托管包）
        from Core.Utils import safe_extract_zip

        staging_dir = self.webui_dir.with_name(f'{self.webui_dir.name}.staging')
        backup_dir = self.webui_dir.with_name(f'{self.webui_dir.name}.backup')
        for path in (staging_dir, backup_dir):
            if path.exists():
                shutil.rmtree(path)
        staging_dir.mkdir(parents=True, exist_ok=True)
        safe_extract_zip(archive_data, staging_dir)
        # 旧目录先改名备份，再切换 staging；切换失败则恢复备份
        if self.webui_dir.exists():
            self.webui_dir.rename(backup_dir)
        try:
            staging_dir.rename(self.webui_dir)
        except Exception:
            if backup_dir.exists():
                backup_dir.rename(self.webui_dir)
            raise
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

    def mount(self, app: FastAPI):
        """挂载 WebUI API 路由到 /webui 前缀下（需在 nonebot.init() 之后、nonebot.run() 之前调用）。"""
        # 函数内导入：api_router 聚合全部路由，部分模块顶层依赖插件托管包，
        # 必须等 NoneBot 插件加载完成后才能导入，避免 uninfo 等被抢先注册为普通模块
        from Core.Web import api_router, setup_cors, setup_request_language
        from Core.Web.Routers.WebSocket import log_sink

        self.app = app
        setup_cors(app)
        setup_request_language(app)
        app.include_router(api_router, prefix='/webui')
        # colorize=True：log_sink 的 str(message) 才带 ANSI 码，前端据此渲染颜色
        logger.add(
            log_sink,
            level='DEBUG',
            format='{time:HH:mm:ss} [<lvl>{level}</lvl>] <light-cyan><u>{name}</u></light-cyan> | {message}\n{exception}',
            colorize=True,
        )
        logger.success('WebUI API routes mounted.')

    def mount_static(self):
        """挂载 WebUI 静态文件到 /webui/ 路径，未命中的前端路由自动回退到 index.html。"""
        if self.app is None:
            logger.warning('WebUI API routes not mounted yet, cannot serve static files.')
            return
        if not (self.webui_dir / 'index.html').exists():
            logger.warning('WebUI static assets missing, only API routes are mounted.')
            self.mount_assets_missing_page()
            return

        @self.app.get('/', include_in_schema=False)
        async def root_redirect():
            """根路径重定向到 /webui/。"""
            return RedirectResponse(url='/webui')

        self.app.frontend('/webui', directory=self.webui_dir, fallback='index.html')
        logger.success('WebUI static files mounted. Visit the root path below to open the WebUi.')

    def mount_assets_missing_page(self):
        """WebUI 资源缺失时挂载根路径提示页，告知静态资源下载失败。"""
        if self.app is None:
            logger.warning('WebUI API routes not mounted yet, cannot serve static files.')
            return

        @self.app.get('/', include_in_schema=False)
        async def assets_missing_page():
            """根路径返回 WebUI 资源加载失败提示页。"""
            lang = 'zh-CN' if get_language() == 'zh' else 'en'
            title = text('webui.assets_missing_title')
            message = text('webui.assets_missing_message')
            retry = text('webui.assets_missing_retry')
            return HTMLResponse(assets_missing_template.format(lang=lang, title=title, message=message, retry=retry))

    async def init(self):
        """初始化：校验并下载 WebUI 静态资源，随后挂载静态文件。"""
        try:
            await self.ensure_downloaded()
        except Exception as error:
            exception_logger.error(f'WebUi download failed, WebUi has been disabled automatically: {error}')
        try:
            self.mount_static()
        except Exception as error:
            exception_logger.error(f'Failed to mount WebUi static files: {error}')


webui_manager = WebUiManager()
