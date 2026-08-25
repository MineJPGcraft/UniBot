import time
from collections import defaultdict

from fastapi import HTTPException, Request

from Scripts.Api.Locale import text
from Scripts.Logging import logger
from Scripts.Managers import task_manager

# 任务管理器中的清理任务名称
CLEANUP_TASK_NAME = 'rate-limiter-cleanup'


class RateLimiter:
    """IP 限流器：监测访问频率，异常 IP 自动封禁一段时间。"""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        base_ban_seconds: int = 60,
        max_ban_seconds: int = 86400,
        backoff_factor: float = 3.0,
        cleanup_interval: int = 60,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.base_ban_seconds = base_ban_seconds
        self.max_ban_seconds = max_ban_seconds
        self.backoff_factor = backoff_factor
        self.cleanup_interval = cleanup_interval

        # {ip: {"timestamps": [float, ...], "banned_until": float | None, "ban_count": int}}
        self.records: dict[str, dict] = defaultdict(lambda: {'timestamps': [], 'banned_until': None, 'ban_count': 0})

    def get_client_ip(self, request: Request) -> str:
        """从请求中获取客户端真实 IP。"""
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        client = request.client
        if client:
            return client.host
        return 'unknown'

    def is_banned(self, ip: str) -> bool:
        """检查 IP 是否在封禁期内。"""
        record = self.records.get(ip)
        if not record or not record['banned_until']:
            return False
        if time.time() >= record['banned_until']:
            record['banned_until'] = None
            return False
        return True

    def record_request(self, ip: str):
        """记录一次请求，清理过期时间戳，判断是否触发封禁。"""
        now = time.time()
        record = self.records[ip]
        timestamps = record['timestamps']

        # 移除超出时间窗口的旧记录
        cutoff = now - self.window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        # 添加当前请求
        timestamps.append(now)

        # 判断是否超出阈值，指数退避封禁时长
        if len(timestamps) > self.max_requests:
            record['ban_count'] += 1
            ban_duration = int(self.base_ban_seconds * (self.backoff_factor ** (record['ban_count'] - 1)))
            ban_duration = min(ban_duration, self.max_ban_seconds)
            record['banned_until'] = now + ban_duration
            logger.warning(
                f'IP [{ip}] 请求频率异常（{len(timestamps)} 次/{self.window_seconds}s），第 {record["ban_count"]} 次封禁 {ban_duration}s！'
            )
            return False

        return True

    async def check(self, request: Request):
        """FastAPI 依赖：检查当前 IP 是否触发限流。"""
        client_ip = self.get_client_ip(request)

        if self.is_banned(client_ip):
            record = self.records[client_ip]
            remain = int(record['banned_until'] - time.time())
            raise HTTPException(
                status_code=429,
                detail=text('limiter.banned_retry', remain=remain),
            )

        allowed = self.record_request(client_ip)
        if not allowed:
            remain = int(self.records[client_ip]['banned_until'] - time.time())
            raise HTTPException(
                status_code=429,
                detail=text('limiter.rate_limited', remain=remain),
            )

    async def cleanup_expired(self):
        """清理一次过期数据，防止内存泄漏。"""
        now = time.time()
        cutoff = now - self.window_seconds
        expired_ips: list[str] = []

        for ip, record in list(self.records.items()):
            # 清理过期时间戳
            timestamps = record['timestamps']
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)

            # 如果 IP 已无记录且未封禁，彻底清理
            if not timestamps and not record['banned_until']:
                expired_ips.append(ip)

            # 清理已过期的封禁状态
            if record['banned_until'] and now >= record['banned_until']:
                record['banned_until'] = None
                if not timestamps:
                    expired_ips.append(ip)

        for ip in expired_ips:
            del self.records[ip]

        if expired_ips:
            logger.debug(f'Rate limiter cleaned up {len(expired_ips)} expired IP records.')

    def start(self):
        """向任务管理器登记后台清理任务。"""
        if task_manager.get(CLEANUP_TASK_NAME) is None:
            task_manager.add(CLEANUP_TASK_NAME, self.cleanup_expired, self.cleanup_interval)
            logger.debug('Rate limiter background cleanup task registered.')

    def stop(self):
        """从任务管理器注销后台清理任务。"""
        if task_manager.remove(CLEANUP_TASK_NAME):
            logger.debug('Rate limiter background cleanup task removed.')


rate_limiter = RateLimiter()
