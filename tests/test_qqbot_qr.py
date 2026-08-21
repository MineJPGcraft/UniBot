"""QQ 官方机器人扫码绑定功能测试。

覆盖：
  - 二维码 PNG 生成与 data URL 封装
  - 单例扫码登录：启动 / 查询 / 取消
  - qr_login 异步生成器：状态产出 / 取消
"""

import asyncio
from unittest.mock import AsyncMock, patch

from Scripts.Connectors.QQOfficial import (
    BindStatus,
    BindTask,
    PollResult,
    QrLoginState,
    _save_credentials_to_env,
    cancel_qr_login,
    generate_qr_png,
    get_qr_login,
    qr_image_data_url,
    qr_login,
    start_qr_login,
)


def test_generate_qr_png_returns_png_bytes():
    """generate_qr_png 应返回合法的 PNG 字节。"""
    png = generate_qr_png('https://example.com/scan')
    assert isinstance(png, bytes)
    assert len(png) > 0
    # PNG 魔数
    assert png[:8] == b'\x89PNG\r\n\x1a\n'


def test_qr_image_data_url_prefix():
    """qr_image_data_url 应返回 base64 PNG data URL。"""
    data_url = qr_image_data_url('https://example.com/scan')
    assert data_url.startswith('data:image/png;base64,')
    assert len(data_url) > len('data:image/png;base64,')


def test_start_and_get_login():
    """启动登录后应能查询到状态，且初始状态为 pending。"""

    async def run():
        state = start_qr_login('test', 'production')
        try:
            assert state.state == 'pending'
            got = get_qr_login()
            assert got is state
        finally:
            cancel_qr_login()

    asyncio.run(run())


def test_cancel_login():
    """取消登录后状态应变为 cancelled，且当前登录被清空。"""

    async def run():
        state = start_qr_login('test', 'production')
        cancelled = cancel_qr_login()
        assert cancelled is True
        assert state.state == 'cancelled'
        # 取消后当前登录被清空
        assert get_qr_login() is None
        # 再次取消：无进行中的登录，返回 False
        assert cancel_qr_login() is False

    asyncio.run(run())


def test_login_to_dict_fields():
    """to_dict 应包含 API 响应所需字段。"""

    async def run():
        state = start_qr_login('test', 'production')
        try:
            data = state.to_dict()
            for key in (
                'state',
                'qr_url',
                'qr_image',
                'app_id',
                'app_secret',
                'error',
            ):
                assert key in data
            assert data['state'] == 'pending'
        finally:
            cancel_qr_login()

    asyncio.run(run())


def test_qr_login_generator_yields_pending_then_completed():
    """qr_login 生成器应先产出 pending（二维码），再产出 completed（凭据）。"""

    async def run():
        task = BindTask(task_id='task-1', key_base64='a2V5')
        poll_result = PollResult(
            status=BindStatus.COMPLETED,
            bot_app_id='app-1',
            bot_encrypt_secret='encrypted',
            user_openid='openid-1',
        )

        connector = AsyncMock()
        connector.__aenter__.return_value = connector
        connector.create_bind_task.return_value = task
        connector.poll_bind_result.return_value = poll_result

        with (
            patch(
                'Scripts.Connectors.QQOfficial.QQBotConnector',
                return_value=connector,
            ),
            patch(
                'Scripts.Connectors.QQOfficial.QQBotConnector.decrypt_secret',
                return_value='secret-1',
            ),
        ):
            states = []
            async for state in qr_login(source='test', env='production'):
                states.append(state)

        assert len(states) == 2
        assert states[0].state == 'pending'
        assert states[0].qr_url
        assert states[0].qr_image.startswith('data:image/png;base64,')
        assert states[1].state == 'completed'
        assert states[1].app_id == 'app-1'
        assert states[1].app_secret == 'secret-1'
        assert states[1].user_openid == 'openid-1'

    asyncio.run(run())


def test_qr_login_generator_cancel_yields_cancelled():
    """取消信号置位后，qr_login 生成器应产出 cancelled 状态。"""

    async def run():
        cancel_event = asyncio.Event()
        cancel_event.set()

        connector = AsyncMock()
        connector.__aenter__.return_value = connector

        with patch(
            'Scripts.Connectors.QQOfficial.QQBotConnector',
            return_value=connector,
        ):
            states = []
            async for state in qr_login(source='test', env='production', cancel_event=cancel_event):
                states.append(state)

        assert len(states) == 1
        assert states[0].state == 'cancelled'
        assert states[0].error == '用户取消'

    asyncio.run(run())


def test_qr_login_state_to_dict():
    """QrLoginState.to_dict 应包含全部 API 字段。"""
    state = QrLoginState(
        state='completed',
        qr_url='https://example.com',
        qr_image='data:image/png;base64,xxx',
        app_id='app-1',
        app_secret='secret-1',
        user_openid='openid-1',
    )
    data = state.to_dict()
    assert data['state'] == 'completed'
    assert data['qr_url'] == 'https://example.com'
    assert data['app_id'] == 'app-1'
    assert data['app_secret'] == 'secret-1'
    assert data['user_openid'] == 'openid-1'


def test_save_credentials_to_env_appends_new_bot():
    """首次保存应把 AppID / Secret 追加为 QQ_BOTS 新条目，并带默认 Intent。"""

    class FakeConfigManager:
        def __init__(self):
            self.environment = {'QQ_BOTS': []}
            self.updated = []

        def read_env(self):
            return self.environment

        def update_env(self, new):
            self.environment.update(new)
            self.updated.append(new)

    fake = FakeConfigManager()
    with patch('Scripts.Connectors.QQOfficial.config_manager', fake):
        _save_credentials_to_env('app-1', 'secret-1')

    bots = fake.environment['QQ_BOTS']
    assert len(bots) == 1
    assert bots[0]['id'] == 'app-1'
    assert bots[0]['secret'] == 'secret-1'
    assert bots[0]['use_websocket'] is True
    assert bots[0]['intent']['c2c_group_at_messages'] is True
    assert fake.updated == [{'QQ_BOTS': bots}]


def test_save_credentials_to_env_updates_existing_bot():
    """相同 AppID 已存在时应更新 Secret，而不是新增条目。"""

    class FakeConfigManager:
        def __init__(self):
            self.environment = {'QQ_BOTS': [{'id': 'app-1', 'secret': 'old'}]}
            self.updated = []

        def read_env(self):
            return self.environment

        def update_env(self, new):
            self.environment.update(new)
            self.updated.append(new)

    fake = FakeConfigManager()
    with patch('Scripts.Connectors.QQOfficial.config_manager', fake):
        _save_credentials_to_env('app-1', 'secret-new')

    bots = fake.environment['QQ_BOTS']
    assert len(bots) == 1
    assert bots[0]['id'] == 'app-1'
    assert bots[0]['secret'] == 'secret-new'


def test_save_credentials_to_env_skips_empty():
    """空 AppID / Secret 不应写入 QQ_BOTS。"""

    class FakeConfigManager:
        def __init__(self):
            self.environment = {'QQ_BOTS': []}
            self.updated = []

        def read_env(self):
            return self.environment

        def update_env(self, new):
            self.environment.update(new)
            self.updated.append(new)

    fake = FakeConfigManager()
    with patch('Scripts.Connectors.QQOfficial.config_manager', fake):
        _save_credentials_to_env('', '')
        _save_credentials_to_env('app-1', '')

    assert fake.environment['QQ_BOTS'] == []
    assert fake.updated == []
