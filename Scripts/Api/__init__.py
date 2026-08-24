from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
api_router.include_router(ws_router)


def setup_cors(app: FastAPI) -> None:
    """配置 CORS，仅允许同源或开发环境 localhost:5173。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
