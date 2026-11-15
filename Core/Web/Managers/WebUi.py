from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from Core.Logging import exception_logger, logger
from Core.Process import is_dev_mode
from Core.Web.Locale import get_language, text

# 前端产物查找路径（两种布局）：
#   - 发布包布局：产物直放 `WebUi/`（`index.html` + `assets/`），不套一层 dist
#   - 本地构建布局：`bun run build` 输出到 `WebUi/dist/`
WEBUI_DIR = Path('WebUi')
WEBUI_DIST_DIR = WEBUI_DIR / 'dist'

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
    """WebUI 管理面板：负责 API 路由挂载与前端构建产物的静态文件挂载。

    WebUI 是核心内置功能，不再提供启停开关；前端源码随核心仓库分发
    （`WebUi/`），构建产物由 `bun run build` 生成。发布包把产物直放 `WebUi/`，
    本地构建则在 `WebUi/dist/`，两者都能被自动识别。
    """

    app: FastAPI | None = None

    @property
    def dist_dir(self) -> Path | None:
        """返回当前可用的前端产物目录，未找到任何产物时返回 None。

        发布包布局优先：源码目录同样存在 `index.html`（Vite 入口），
        因此以 `assets/` 目录是否存在判定该目录是否已被构建产物替换。
        """
        if (WEBUI_DIR / 'assets').is_dir() and (WEBUI_DIR / 'index.html').is_file():
            return WEBUI_DIR
        if (WEBUI_DIST_DIR / 'index.html').is_file():
            return WEBUI_DIST_DIR
        return None

    def is_ready(self) -> bool:
        """检查前端构建产物是否存在。"""
        return self.dist_dir is not None

    def mount(self, app: FastAPI):
        """挂载 WebUI API 路由到 /webui 前缀下（需在 nonebot.init() 之后、nonebot.run() 之前调用）。"""
        # 函数内导入：api_router 聚合全部路由，部分模块顶层依赖插件托管包，
        # 必须等 NoneBot 插件加载完成后才能导入，避免 uninfo 等被抢先注册为普通模块
        from Core.Web import (
            api_router,
            setup_compression,
            setup_cors,
            setup_request_language,
            setup_static_cache_headers,
        )
        from Core.Web.Routers.WebSocket import log_sink

        self.app = app
        setup_cors(app)
        setup_static_cache_headers(app)
        setup_request_language(app)
        # 压缩最后注册：Starlette 后注册的中间件位于外层，保证压缩作用在所有响应上
        setup_compression(app)
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
        if is_dev_mode():
            # 开发模式：前端由 Vite dev server 提供（含热更新），后端不托管本地产物，
            # 也不注册任何前端页面路由（访问后端端口只会得到 404）
            logger.info(
                'WebUI dev mode: static files are not mounted. '
                'Run `bun run dev` in WebUi/ and open the Vite dev server (default http://localhost:5173/webui/).'
            )
            return
        dist_dir = self.dist_dir
        if dist_dir is None:
            logger.warning('WebUI build output missing, only API routes are mounted.')
            self.mount_assets_missing_page()
            return

        @self.app.get('/', include_in_schema=False)
        async def root_redirect():
            """根路径重定向到 /webui/。"""
            return RedirectResponse(url='/webui')

        self.app.frontend('/webui', directory=dist_dir, fallback='index.html')
        logger.success('WebUI static files mounted. Visit the root path below to open the WebUI.')

    def mount_assets_missing_page(self):
        """前端构建产物缺失时挂载根路径提示页，告知如何构建。"""
        if self.app is None:
            logger.warning('WebUI API routes not mounted yet, cannot serve static files.')
            return

        @self.app.get('/', include_in_schema=False)
        async def assets_missing_page():
            """根路径返回 WebUI 构建产物缺失提示页。"""
            lang = 'zh-CN' if get_language() == 'zh' else 'en'
            title = text('webui.assets_missing_title')
            message = text('webui.assets_missing_message')
            retry = text('webui.assets_missing_retry')
            return HTMLResponse(assets_missing_template.format(lang=lang, title=title, message=message, retry=retry))

    def init(self):
        """初始化：挂载静态文件（dev 模式或产物缺失时只保留 API 路由）。"""
        try:
            self.mount_static()
        except Exception as error:
            exception_logger.error(f'Failed to mount WebUI static files: {error}')


webui_manager = WebUiManager()
