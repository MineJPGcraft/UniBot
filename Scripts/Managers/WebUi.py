import shutil
from pathlib import Path
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from Scripts.Logging import exception_logger, logger
from Scripts.Network import github_download

from .Config import config_manager


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
            logger.info(f'WebUI static assets ready (v{self.version}).')
            return True
        logger.info(f'Downloading WebUI static assets (v{self.version})...')
        url = f'https://github.com/MineJPGcraft/UniBot.WebUi/releases/download/{self.version}/WebUi.zip'
        if not (response := await github_download(url)):
            logger.warning(f'Failed to download WebUI (v{self.version}), check your network and retry later.')
            return False
        try:
            if self.webui_dir.exists():
                shutil.rmtree(self.webui_dir)
            self.webui_dir.mkdir(parents=True, exist_ok=True)
            with ZipFile(response) as zip_file:
                zip_file.extractall(self.webui_dir)
            self.version_file.write_text(self.version, encoding='Utf-8')
        except Exception as error:
            logger.warning(f'Failed to extract WebUI static assets: {error}')
            return False
        logger.success(f'WebUI static assets downloaded ({self.version}).')
        return True

    def mount(self, app: FastAPI):
        """挂载 WebUI API 路由到 /webui 前缀下（需在 nonebot.init() 之后、nonebot.run() 之前调用）。"""
        # 函数内导入：Scripts.Api 依赖本模块的 webui_manager（认证/日志等），
        # 且须在 nonebot 初始化完成后才可挂载路由，延迟导入避免初始化期循环依赖
        from Scripts.Api import api_router, setup_cors
        from Scripts.Api.WebSocket import log_sink

        self.app = app
        setup_cors(app)
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
            return

        @self.app.get('/', include_in_schema=False)
        async def root_redirect():
            """根路径重定向到 /webui/。"""
            return RedirectResponse(url='/webui')

        self.app.frontend('/webui', directory=self.webui_dir, fallback='index.html')
        logger.success('WebUI static files mounted. Visit the root path below to open the WebUi.')

    async def init(self):
        """初始化：校验并下载 WebUI 静态资源，随后挂载静态文件。"""
        try:
            await self.ensure_downloaded()
            self.mount_static()
        except Exception as error:
            exception_logger.error(f'WebUi download failed, WebUi has been disabled automatically: {error}')


webui_manager = WebUiManager()
