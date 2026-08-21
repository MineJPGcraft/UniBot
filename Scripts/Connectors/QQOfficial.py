"""
QQ Bot Connector — 异步扫码登录实现（httpx）

来源参考：tencent-connect/dsh-qqbot 仓库（src/setup.ts）调用 @tencent-connect/qqbot-connector
SDK 完成扫码。该 npm 包内置的 qqbot-session 模块直接对接 q.qq.com 的两个内部接口：

  1. POST https://q.qq.com/lite/create_bind_task     —— 创建绑定任务，返回 task_id
  2. POST https://q.qq.com/lite/poll_bind_result      —— 轮询扫码结果

扫码 URL（始终使用生产域名）：
  https://q.qq.com/qqbot/openclaw/connect.html?task_id=<id>&source=<source>&_wv=2

用户手机 QQ 扫码确认后，后端返回 AES-256-GCM 加密的 AppSecret：
  密文格式（base64 解码后）: IV(12B) + ciphertext(NB) + AuthTag(16B)
  key 为 create_bind_task 时本地生成的 32 字节随机数（base64）

本文件将该流程用 Python + httpx 异步重写，提供：
  - QQBotConnector：低层 HTTP/AES 接口
  - qr_login()：统一扫码登录入口（异步生成器，每次 yield 一个 QrLoginState）
  - start_qr_login() / get_qr_login() / cancel_qr_login()：WebUI 单例扫码登录
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import IntEnum

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from nonebot.log import logger

from Scripts.Managers import config_manager

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #

PRODUCTION_HOST = 'q.qq.com'
TEST_HOST = 'test.q.qq.com'

# 二维码落地页始终使用生产域名（即使 SDK 运行在 test 模式）
QR_LANDING_HOST = PRODUCTION_HOST
QR_LANDING_PATH = '/qqbot/openclaw/connect.html'

CREATE_BIND_TASK_PATH = '/lite/create_bind_task'
POLL_BIND_RESULT_PATH = '/lite/poll_bind_result'

DEFAULT_HTTP_TIMEOUT = 10.0  # 单次 HTTP 请求超时（秒）
DEFAULT_POLL_INTERVAL = 2.0  # 轮询间隔（秒）—— 与官方 SDK 保持一致
DEFAULT_HTTP_PER_REQUEST_TIMEOUT = 10  # 与 SDK 一致（10s）


class BindStatus(IntEnum):
    """poll_bind_result.data.status 枚举"""

    NONE = 0  # 未知/初始
    PENDING = 1  # 已生成二维码，等待扫码 / 已扫码等待确认
    COMPLETED = 2  # 用户确认完成
    EXPIRED = 3  # 二维码过期


# --------------------------------------------------------------------------- #
# 数据类
# --------------------------------------------------------------------------- #


@dataclass
class BindTask:
    """create_bind_task 的返回结果"""

    task_id: str
    key_base64: str  # 本地生成的 32 字节随机 key（base64）


@dataclass
class PollResult:
    """poll_bind_result 的返回结果（已规整过字段名）"""

    status: BindStatus
    bot_app_id: str = ''
    bot_encrypt_secret: str = ''  # base64 编码的 IV+ciphertext+AuthTag
    user_openid: str | None = None


@dataclass
class QrConnectCredentials:
    """扫码成功后得到的最终凭据"""

    app_id: str
    app_secret: str
    user_openid: str | None = None


# --------------------------------------------------------------------------- #
# 异常
# --------------------------------------------------------------------------- #


class QQBotConnectorError(RuntimeError):
    """所有 connector 相关错误的基类"""


class CreateBindTaskError(QQBotConnectorError):
    """create_bind_task 失败"""


class PollBindResultError(QQBotConnectorError):
    """poll_bind_result 失败"""


class QrConnectCancelled(QQBotConnectorError):
    """扫码流程被外部取消"""


class QrConnectTimeout(QQBotConnectorError):
    """整体流程超时"""


# --------------------------------------------------------------------------- #
# 低层：QQBotConnector
# --------------------------------------------------------------------------- #


class QQBotConnector:
    """
    直接对接 q.qq.com 的低层 HTTP 接口。

    每个方法都是独立的 HTTP 调用，可单独使用。
    完整扫码流程由 `qr_login` 统一编排。
    """

    def __init__(
        self,
        env: str = 'production',
        timeout: float = DEFAULT_HTTP_PER_REQUEST_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.env = env
        self.timeout = timeout
        # 允许调用方传入共享 client（推荐，便于连接复用与统一关闭）
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> QQBotConnector:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # ---- 内部工具 ---- #

    @property
    def _host(self) -> str:
        return TEST_HOST if self.env == 'test' else PRODUCTION_HOST

    @property
    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                'QQBotConnector client not initialized, use `async with QQBotConnector() as c:` or pass client= explicitly'
            )
        return self._client

    async def _post_json(self, url: str, body: dict) -> dict:
        """POST JSON 并解析响应。失败时抛出 QQBotConnectorError。"""
        client = self._client_or_raise
        try:
            resp = await client.post(
                url,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                content=json.dumps(body, separators=(',', ':')).encode('Utf-8'),
            )
        except httpx.HTTPError as e:
            raise QQBotConnectorError(f'HTTP request failed: {url} -> {e}') from e

        if resp.status_code != 200:
            raise QQBotConnectorError(f'HTTP {resp.status_code} from {url}')

        try:
            return resp.json()
        except Exception as e:
            raise QQBotConnectorError(f'Response is not JSON: {resp.text!r}') from e

    # ---- 公开 API ---- #

    async def create_bind_task(self) -> BindTask:
        """
        创建绑定任务。

        本地生成 32 字节随机 key（base64），POST 给 q.qq.com，换取 task_id。
        该 key 后续用于解密 bot_encrypt_secret，必须保存。
        """
        url = f'https://{self._host}{CREATE_BIND_TASK_PATH}'
        key_b64 = base64.b64encode(secrets.token_bytes(32)).decode('ascii')
        resp = await self._post_json(url, {'key': key_b64})

        if resp.get('retcode') != 0:
            raise CreateBindTaskError(resp.get('msg') or 'create_bind_task failed')

        data = resp.get('data') or {}
        task_id = data.get('task_id')
        if not task_id:
            raise CreateBindTaskError('create_bind_task: missing task_id')
        return BindTask(task_id=task_id, key_base64=key_b64)

    async def poll_bind_result(self, task_id: str) -> PollResult:
        """轮询扫码结果。"""
        url = f'https://{self._host}{POLL_BIND_RESULT_PATH}'
        resp = await self._post_json(url, {'task_id': task_id})

        if resp.get('retcode') != 0:
            raise PollBindResultError(resp.get('msg') or 'poll_bind_result failed')

        data = resp.get('data') or {}
        return PollResult(
            status=BindStatus(int(data.get('status') or 0)),
            bot_app_id=str(data.get('bot_appid') or ''),
            bot_encrypt_secret=str(data.get('bot_encrypt_secret') or ''),
            user_openid=data.get('user_openid') or None,
        )

    # ---- 静态工具 ---- #

    @staticmethod
    def build_connect_url(task_id: str, source: str = '') -> str:
        """
        构造扫码 URL（手机 QQ 扫描后会跳转到绑定页面）。

        注意：URL 始终使用生产域名 q.qq.com，即使 SDK 运行在 test 模式。
        """
        from urllib.parse import quote

        return f'https://{QR_LANDING_HOST}{QR_LANDING_PATH}?task_id={quote(task_id, safe="")}&source={quote(source, safe="")}&_wv=2'

    @staticmethod
    def decrypt_secret(encrypted_base64: str, key_base64: str) -> str:
        """
        AES-256-GCM 解密 bot_encrypt_secret。

        密文结构（base64 解码后）：
            IV(12B) + ciphertext(NB) + AuthTag(16B)

        Args:
            encrypted_base64: poll_bind_result 返回的 bot_encrypt_secret
            key_base64: create_bind_task 时本地生成的 32 字节 key（base64）

        Returns:
            解密后的明文 AppSecret（utf-8 字符串）
        """
        raw = base64.b64decode(encrypted_base64)
        if len(raw) < 12 + 16:
            raise ValueError('encrypted payload too short')

        iv = raw[:12]
        ciphertext_with_tag = raw[12:]  # cryptography 库需要 ciphertext + tag 拼在一起
        key = base64.b64decode(key_base64)
        if len(key) != 32:
            raise ValueError(f'AES-256-GCM key must be 32 bytes, got {len(key)}')

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data=None)
        return plaintext.decode('utf-8')


# --------------------------------------------------------------------------- #
# 扫码登录状态
# --------------------------------------------------------------------------- #


@dataclass
class QrLoginState:
    """扫码登录的状态快照，由 `qr_login` 生成器逐步产出。"""

    state: str = 'pending'  # pending / completed / failed / cancelled
    qr_url: str = ''
    qr_image: str = ''  # 二维码 data URL（base64 PNG）
    app_id: str = ''
    app_secret: str = ''
    user_openid: str | None = None
    error: str = ''

    def to_dict(self) -> dict:
        """转为 API 响应用的字典。"""
        return {
            'state': self.state,
            'qr_url': self.qr_url,
            'qr_image': self.qr_image,
            'app_id': self.app_id,
            'app_secret': self.app_secret,
            'user_openid': self.user_openid,
            'error': self.error,
        }


# --------------------------------------------------------------------------- #
# 统一扫码登录（异步生成器）
# --------------------------------------------------------------------------- #


async def qr_login(
    source: str = '',
    env: str = 'production',
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    total_timeout: float | None = None,
    cancel_event: asyncio.Event | None = None,
) -> AsyncIterator[QrLoginState]:
    """
    统一的 QQ 扫码登录入口（异步生成器）。

    完整流程：创建绑定任务 → 产出二维码状态 → 轮询扫码结果 → 产出凭据状态。
    二维码过期会自动刷新并产出新的二维码状态；被取消或超时产出终态后结束。

    每次 `yield` 一个 `QrLoginState`（含二维码 data URL / 凭据 / 错误信息），
    调用方用 `async for state in qr_login():` 消费即可，天然适配 SSE 推送。

    Args:
        source: 扫码来源标识（透传给 q.qq.com）
        env: 环境，'production' 或 'test'
        poll_interval: 轮询间隔（秒）
        total_timeout: 整体超时（秒），None 表示不限制
        cancel_event: 外部取消信号，置位后流程终止

    Yields:
        每次状态变化产出一个 `QrLoginState`：
          - pending：二维码已生成（含 qr_url / qr_image），或过期后刷新
          - completed：扫码成功（含 app_id / app_secret / user_openid）
          - failed：流程失败（含 error）
          - cancelled：被外部取消（含 error）
    """
    try:
        async with QQBotConnector(env=env) as connector:
            while not (cancel_event is not None and cancel_event.is_set()):
                task = await connector.create_bind_task()
                qr_url = QQBotConnector.build_connect_url(task.task_id, source)

                logger.info('QQ QR code login: scan the QR code with your phone QQ to complete binding')
                logger.info(f'QR code link: {qr_url}')
                yield QrLoginState(state='pending', qr_url=qr_url, qr_image=qr_image_data_url(qr_url))

                outcome = await _poll_until_settled(
                    connector,
                    task,
                    poll_interval=poll_interval,
                    cancel_event=cancel_event,
                )
                if outcome is not None:
                    logger.info(f'QQ QR code login succeeded: app_id={outcome.app_id}')
                    yield QrLoginState(
                        state='completed',
                        app_id=outcome.app_id,
                        app_secret=outcome.app_secret,
                        user_openid=outcome.user_openid,
                    )
                    return

                # 二维码过期，刷新后继续
                logger.warning('QQ QR code expired, refreshing...')
    except QrConnectCancelled:
        yield QrLoginState(state='cancelled', error='用户取消')
        return
    except Exception as error:
        logger.error(f'QQ QR code login failed: {error}')
        yield QrLoginState(state='failed', error=str(error) or error.__class__.__name__)
        return

    # 循环因取消信号退出（未抛异常路径）
    if cancel_event is not None and cancel_event.is_set():
        yield QrLoginState(state='cancelled', error='用户取消')


async def _poll_until_settled(
    connector: QQBotConnector,
    task: BindTask,
    poll_interval: float,
    cancel_event: asyncio.Event | None,
) -> QrConnectCredentials | None:
    """
    轮询直到拿到凭据（返回）或二维码过期（返回 None）。
    抛出 QrConnectCancelled 表示被外部取消。
    """
    while not (cancel_event is not None and cancel_event.is_set()):
        try:
            result = await connector.poll_bind_result(task.task_id)
        except PollBindResultError as e:
            # 单次轮询失败不应终止流程，与官方 SDK 行为一致
            logger.warning(f'Polling QR code result failed: {e}, retrying in {poll_interval}s')
            await _sleep_or_cancel(poll_interval, cancel_event)
            continue

        if result.status == BindStatus.COMPLETED:
            if not result.bot_app_id or not result.bot_encrypt_secret:
                # 后端异常，重新发起
                return None
            app_secret = QQBotConnector.decrypt_secret(result.bot_encrypt_secret, task.key_base64)
            return QrConnectCredentials(
                app_id=result.bot_app_id,
                app_secret=app_secret,
                user_openid=result.user_openid,
            )

        if result.status == BindStatus.EXPIRED:
            return None

        # PENDING / NONE → 继续轮询
        await _sleep_or_cancel(poll_interval, cancel_event)

    raise QrConnectCancelled('用户取消')


async def _sleep_or_cancel(seconds: float, cancel_event: asyncio.Event | None) -> None:
    """等待指定秒数，期间若收到取消信号则抛出 QrConnectCancelled。"""
    if cancel_event is None:
        await asyncio.sleep(seconds)
        return
    try:
        await asyncio.wait_for(cancel_event.wait(), timeout=seconds)
        # 未超时返回说明取消信号被触发
        raise QrConnectCancelled('用户取消')
    except TimeoutError:
        return


# --------------------------------------------------------------------------- #
# 二维码图片生成（供 WebUI 展示）
# --------------------------------------------------------------------------- #


def generate_qr_png(url: str, box_size: int = 8, border: int = 2) -> bytes:
    """生成二维码 PNG 字节（依赖 qrcode 库，未安装时抛 ImportError）。"""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def qr_image_data_url(url: str) -> str:
    """生成二维码 data URL（base64 PNG），可直接用于前端 `<img>`。"""
    encoded = base64.b64encode(generate_qr_png(url)).decode('ascii')
    return f'data:image/png;base64,{encoded}'


# --------------------------------------------------------------------------- #
# 单例扫码登录（供 WebUI 调用）
# --------------------------------------------------------------------------- #


@dataclass
class _LoginSession:
    """一次扫码登录会话：持有状态快照、取消信号与后台任务。"""

    state: QrLoginState
    cancel_event: asyncio.Event
    task: asyncio.Task


# 全局单例：同一时刻只允许一个扫码登录
current_session: _LoginSession | None = None


def start_qr_login(source: str = '', env: str = 'production') -> QrLoginState:
    """
    启动一次扫码登录（若已有进行中的登录则先取消）。

    立即返回状态对象（含二维码 data URL），后台任务驱动 `qr_login` 生成器，
    把最新状态写入 `QrLoginState`，WebUI 只需轮询查询。
    """
    global current_session
    cancel_qr_login()
    state = QrLoginState()
    cancel_event = asyncio.Event()
    task = asyncio.create_task(_run_login(state, cancel_event, source=source, env=env))
    current_session = _LoginSession(state=state, cancel_event=cancel_event, task=task)
    return state


def get_qr_login() -> QrLoginState | None:
    """获取当前扫码登录状态（无进行中的登录返回 None）。"""
    return current_session.state if current_session is not None else None


def cancel_qr_login() -> bool:
    """取消当前扫码登录，返回是否存在进行中的登录。"""
    global current_session
    session = current_session
    if session is None:
        return False
    session.state.state = 'cancelled'
    session.state.error = '用户取消'
    session.cancel_event.set()
    current_session = None
    return True


def _save_credentials_to_env(app_id: str, app_secret: str) -> None:
    """把扫码登录得到的 AppID / Secret 写入 .env 的 QQ_BOTS 配置。

    若 QQ_BOTS 中已存在相同 AppID 的机器人则更新其 Secret，否则追加新条目。
    新条目使用默认 Intent 订阅与 WebSocket 连接方式，用户可在 WebUI 中再调整。
    """
    if not app_id or not app_secret:
        return
    bots = list(config_manager.read_env().get('QQ_BOTS') or [])
    default_intent = {
        'guilds': False,
        'guild_members': False,
        'guild_messages': False,
        'guild_message_reactions': False,
        'direct_message': False,
        'open_forum_event': False,
        'audio_live_member': False,
        'c2c_group_at_messages': True,
        'interaction': False,
        'message_audit': False,
        'forum_event': False,
        'audio_action': False,
        'at_messages': False,
    }
    for bot in bots:
        if isinstance(bot, dict) and bot.get('id') == app_id:
            bot['secret'] = app_secret
            break
    else:
        bots.append(
            {
                'id': app_id,
                'secret': app_secret,
                'token': '',
                'intent': default_intent,
                'use_websocket': True,
            }
        )
    config_manager.update_env({'QQ_BOTS': bots})


async def _run_login(state: QrLoginState, cancel_event: asyncio.Event, source: str, env: str) -> None:
    """驱动后台扫码登录，生成器产出的每个状态写入 state。"""
    try:
        async for snapshot in qr_login(
            source=source,
            env=env,
            cancel_event=cancel_event,
        ):
            state.state = snapshot.state
            state.qr_url = snapshot.qr_url
            state.qr_image = snapshot.qr_image
            state.app_id = snapshot.app_id
            state.app_secret = snapshot.app_secret
            state.user_openid = snapshot.user_openid
            state.error = snapshot.error
            # 登录成功：自动把凭据持久化到 .env 的 QQ_BOTS
            if snapshot.state == 'completed':
                _save_credentials_to_env(snapshot.app_id, snapshot.app_secret)
    except Exception as error:
        # 生成器内部异常，兜底写入失败状态
        if state.state not in ('completed', 'failed', 'cancelled'):
            state.state = 'failed'
            state.error = str(error) or error.__class__.__name__
