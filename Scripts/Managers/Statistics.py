"""
数据统计管理器：聚合机器人收发消息量、群聊活跃度并持久化到 Data/Statistics.json。

仅依赖标准库，可在插件加载前的早期链路安全导入。
"""

import asyncio
from asyncio import Lock
from datetime import UTC, datetime, timedelta
from json import dumps, loads

from Scripts.Constants import STATISTICS_FILE
from Scripts.Logging import logger

# 按天趋势与群聊明细的保留时长，超出后落盘前清理
DAILY_RETENTION_DAYS = 90
GROUP_RETENTION_DAYS = 30


def _today() -> str:
    """当前日期（本地时区）的 ISO 字符串。"""
    return datetime.now().astimezone().date().isoformat()


class StatisticsManager:
    """数据统计管理器：记录收发消息计数、按天趋势、群聊活跃度。"""

    def __init__(self) -> None:
        self.started_at: str = datetime.now(UTC).isoformat()
        self.sent_total: int = 0
        self.received_total: int = 0
        # 发送消息按目标场景细分（group / private / unknown）
        self.sent_kinds: dict[str, int] = {}
        self.group_received_total: int = 0
        self.private_received_total: int = 0
        # 按天趋势：{日期: {'sent': n, 'received': n, 'groups': {group_key: n}}}
        self.daily: dict[str, dict] = {}
        # 群聊累计：{group_key: {'name', 'platform', 'received', 'last_active'}}
        self.groups: dict[str, dict] = {}
        # 收到消息的平台分布：{平台名: n}
        self.platforms: dict[str, int] = {}
        self.dirty = False
        self.lock = Lock()
        self.statistics_file = STATISTICS_FILE

    def record_sent(self, target_kind: str = 'unknown') -> None:
        """记录一条机器人发出的消息，target_kind 为目标场景类型。"""
        self.sent_total += 1
        self.sent_kinds[target_kind] = self.sent_kinds.get(target_kind, 0) + 1
        self._day_bucket()['sent'] += 1
        self.dirty = True

    def record_received(self, platform: str, group_key: str | None = None, group_name: str | None = None) -> None:
        """记录一条收到的消息；提供 group_key 时同步计入群聊与活跃度。"""
        self.received_total += 1
        self.platforms[platform] = self.platforms.get(platform, 0) + 1
        day_bucket = self._day_bucket()
        day_bucket['received'] += 1
        if group_key is not None:
            self.group_received_total += 1
            day_bucket.setdefault('groups', {})
            day_bucket['groups'][group_key] = day_bucket['groups'].get(group_key, 0) + 1
            group_entry = self.groups.get(group_key)
            if group_entry is None:
                self.groups[group_key] = {
                    'name': group_name,
                    'platform': platform,
                    'received': 1,
                    'last_active': datetime.now(UTC).timestamp(),
                }
            else:
                group_entry['received'] += 1
                group_entry['last_active'] = datetime.now(UTC).timestamp()
                if group_name and not group_entry.get('name'):
                    group_entry['name'] = group_name
        else:
            self.private_received_total += 1
        self.dirty = True

    def summary(self) -> dict:
        """返回总览数据（含今日增量与活跃群聊数）。"""
        today = _today()
        today_bucket = self.daily.get(today, {})
        groups_today = today_bucket.get('groups', {})
        return {
            'started_at': self.started_at,
            'sent_total': self.sent_total,
            'received_total': self.received_total,
            'sent_group': self.sent_kinds.get('group', 0),
            'sent_private': self.sent_kinds.get('private', 0),
            'group_received_total': self.group_received_total,
            'private_received_total': self.private_received_total,
            'today_sent': today_bucket.get('sent', 0),
            'today_received': today_bucket.get('received', 0),
            'active_groups_today': len(groups_today),
            'tracked_groups': len(self.groups),
        }

    def trend(self, days: int = 30) -> list[dict]:
        """返回最近 N 天（含今日）的每日趋势，缺失日期补零。"""
        result = []
        for offset in range(days - 1, -1, -1):
            date = (datetime.now().astimezone().date() - timedelta(days=offset)).isoformat()
            bucket = self.daily.get(date, {})
            result.append(
                {
                    'date': date,
                    'sent': bucket.get('sent', 0),
                    'received': bucket.get('received', 0),
                    'active_groups': len(bucket.get('groups', {})),
                }
            )
        return result

    def top_groups(self, limit: int = 20) -> list[dict]:
        """按最近活跃时间倒序返回群聊列表（最多 limit 个）。"""
        entries = [
            {'key': key, **data}
            for key, data in sorted(self.groups.items(), key=lambda item: item[1]['last_active'], reverse=True)
        ]
        return entries[:limit]

    def platform_rank(self) -> list[dict]:
        """按消息量倒序返回平台分布。"""
        return [
            {'platform': platform, 'count': count}
            for platform, count in sorted(self.platforms.items(), key=lambda item: item[1], reverse=True)
        ]

    async def save(self) -> None:
        """将统计数据持久化到磁盘（清理超期历史后写入）。"""
        async with self.lock:
            content = self._export_data()
            await asyncio.to_thread(
                self.statistics_file.write_text,
                dumps(content, ensure_ascii=False, indent=2),
                'Utf-8',
            )
            self.dirty = False

    def load(self) -> None:
        """从磁盘加载统计数据，文件损坏时回退为空数据。"""
        if not self.statistics_file.exists():
            logger.info('Statistics file does not exist, starting with empty data.')
            return
        try:
            stored = loads(self.statistics_file.read_text('Utf-8'))
            assert isinstance(stored, dict)
        except Exception:
            logger.warning('Statistics file is corrupted, falling back to empty data.')
            return
        self.started_at = stored.get('started_at') or datetime.now(UTC).isoformat()
        self.sent_total = stored.get('sent_total', 0)
        self.received_total = stored.get('received_total', 0)
        self.sent_kinds = stored.get('sent_kinds', {})
        self.group_received_total = stored.get('group_received_total', 0)
        self.private_received_total = stored.get('private_received_total', 0)
        self.daily = stored.get('daily', {})
        self.groups = stored.get('groups', {})
        self.platforms = stored.get('platforms', {})
        logger.success('Statistics data loaded successfully.')

    def reset(self) -> None:
        """清空全部统计数据并重置统计起始时间。"""
        fresh = StatisticsManager()
        self.started_at = fresh.started_at
        self.sent_total = 0
        self.received_total = 0
        self.sent_kinds = {}
        self.group_received_total = 0
        self.private_received_total = 0
        self.daily = {}
        self.groups = {}
        self.platforms = {}
        self.dirty = True

    def _day_bucket(self) -> dict:
        """获取今日的趋势桶，不存在时初始化。"""
        today = _today()
        if today not in self.daily:
            self.daily[today] = {'sent': 0, 'received': 0, 'groups': {}}
        return self.daily[today]

    def _prune_history(self) -> None:
        """清理超过保留时长的按天趋势与长期不活跃的群聊记录。"""
        cutoff_date = (datetime.now().astimezone().date() - timedelta(days=DAILY_RETENTION_DAYS)).isoformat()
        for date in [date for date in self.daily if date < cutoff_date]:
            del self.daily[date]
        active_cutoff = (datetime.now(UTC) - timedelta(days=GROUP_RETENTION_DAYS)).timestamp()
        for group_key in [key for key, entry in self.groups.items() if entry['last_active'] < active_cutoff]:
            del self.groups[group_key]

    def _export_data(self) -> dict:
        """导出可序列化的统计数据快照（先清理超期历史）。"""
        self._prune_history()
        return {
            'started_at': self.started_at,
            'sent_total': self.sent_total,
            'received_total': self.received_total,
            'sent_kinds': self.sent_kinds,
            'group_received_total': self.group_received_total,
            'private_received_total': self.private_received_total,
            'daily': self.daily,
            'groups': self.groups,
            'platforms': self.platforms,
        }


statistics_manager = StatisticsManager()
