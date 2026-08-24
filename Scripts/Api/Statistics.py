import nonebot
from fastapi import APIRouter, Depends, Query

from Scripts.Managers import statistics_manager

from .Auth import get_current_user, require_role

router = APIRouter(prefix='/api/statistics', tags=['Statistics'])

# 趋势查询的默认与最大天数
DEFAULT_TREND_DAYS = 30
MAX_TREND_DAYS = 90


def get_connected_bots() -> list[dict]:
    """收集当前已连接的机器人账号信息。"""
    return [{'self_id': str(self_id), 'adapter': bot.adapter.get_name()} for self_id, bot in nonebot.get_bots().items()]


@router.get('', summary='获取消息统计数据')
async def get_statistics(
    days: int = Query(DEFAULT_TREND_DAYS, ge=1, le=MAX_TREND_DAYS, description='趋势天数'),
    current_user: dict = Depends(get_current_user),
):
    """获取机器人发言、群聊消息、活跃群聊统计与当前已连接的机器人列表。"""
    return {
        'code': 0,
        'data': {
            'summary': statistics_manager.summary(),
            'trend': statistics_manager.trend(days),
            'groups': statistics_manager.top_groups(),
            'platforms': statistics_manager.platform_rank(),
            'bots': get_connected_bots(),
        },
        'message': 'ok',
    }


@router.post('/reset', summary='清空统计数据', dependencies=[Depends(require_role('admin'))])
async def reset_statistics():
    """清空全部统计数据并立即落盘。"""
    statistics_manager.reset()
    await statistics_manager.save()
    return {'code': 0, 'data': None, 'message': '统计数据已清空'}
