"""WebUI REST / WebSocket 路由聚合子包。

每个领域一个路由模块（`Auth` / `Users` / `Status` / `Config` / `Servers` / `Statistics` /
`Players` / `Logs` / `Plugins` / `Extensions` / `Tasks` / `WebSocket`），平台连接类路由放
`Connectors/`。本文件收集全部路由到统一的 `api_router`，由 `Core.Web` 挂载到 `/webui` 前缀。
"""

from fastapi import APIRouter

from .Auth import router as auth_router
from .Config import router as config_router
from .Connectors.QQBot import router as qqbot_router
from .Extensions import router as extensions_router
from .Logs import router as logs_router
from .Players import router as players_router
from .Plugins import router as plugins_router
from .Servers import router as servers_router
from .Statistics import router as statistics_router
from .Status import router as status_router
from .Tasks import router as tasks_router
from .Users import router as users_router
from .WebSocket import router as ws_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(status_router)
api_router.include_router(config_router)
api_router.include_router(servers_router)
api_router.include_router(statistics_router)
api_router.include_router(players_router)
api_router.include_router(logs_router)
api_router.include_router(plugins_router)
api_router.include_router(qqbot_router)
api_router.include_router(extensions_router)
api_router.include_router(tasks_router)
api_router.include_router(ws_router)
