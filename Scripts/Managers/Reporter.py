"""匿名运行数据上报器：登记机器并定时上报非敏感运行统计。"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
import uuid
from pathlib import Path

from Scripts.Logging import logger
from Scripts.Network import post_request

REPORTER_SERVER_URL = 'https://bot-api.mcjpg.dev'
REPORT_INTERVAL_SECONDS = 300


class Reporter:
    """负责机器在线状态、连接机器人数量和消息统计的匿名上报。"""

    machine_id: str = ''

    def __init__(self) -> None:
        self._report_task: asyncio.Task | None = None

    def init(self) -> None:
        """初始化机器 ID。"""
        self.machine_id = self.generate_machine_id()
        logger.info('Reporter identifier initialized.')

    def generate_machine_id(self) -> str:
        """基于固定机器标识生成不可逆机器 ID。"""
        machine_identifier = self.collect_machine_identifier() + ':MC-UniBot'
        return hashlib.sha256(machine_identifier.encode('Utf-8')).hexdigest()

    def collect_machine_identifier(self) -> str:
        """按平台优先级获取稳定的机器标识。"""
        machine_id_path = Path('/etc/machine-id')
        if machine_id_path.exists():
            machine_id = machine_id_path.read_text('Utf-8').strip()
            if machine_id:
                return machine_id
        hardware_uuid = self.get_macos_hardware_uuid()
        if hardware_uuid:
            return hardware_uuid
        machine_guid = self.get_windows_machine_guid()
        if machine_guid:
            return machine_guid
        mac_address = self.get_mac_address()
        if mac_address:
            return mac_address
        return '?'

    def get_windows_machine_guid(self) -> str:
        """读取 Windows 注册表 MachineGuid。"""
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography') as key:
                return str(winreg.QueryValueEx(key, 'MachineGuid')[0]).strip()
        except Exception:
            return ''

    def get_macos_hardware_uuid(self) -> str:
        """读取 macOS 硬件 UUID。"""
        try:
            result = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                if 'IOPlatformUUID' in line:
                    return line.split('"')[-2]
        except Exception:
            pass
        return ''

    def get_mac_address(self) -> str:
        """获取本机网卡 MAC 地址。"""
        try:
            mac_address = uuid.getnode()
            if mac_address & 0xFFFFFFFFFFFF:
                return ':'.join(f'{(mac_address >> shift) & 0xFF:02x}' for shift in range(40, -1, -8))
        except Exception:
            pass
        return ''

    def collect_report(self) -> dict[str, int | str]:
        """收集不含机器身份和消息内容的运行统计。"""
        from nonebot import get_bots

        from Scripts.Managers import statistics_manager

        summary = statistics_manager.summary()
        return {
            'id': self.machine_id,
            'bot_count': len(get_bots()),
            'group_count': summary['tracked_groups'],
            'today_sent': summary['today_sent'],
            'today_received': summary['today_received'],
            'sent_total': summary['sent_total'],
            'received_total': summary['received_total'],
        }

    async def report(self) -> bool:
        """上报一次在线状态和运行统计。"""
        data = await post_request(f'{REPORTER_SERVER_URL}/report.php', self.collect_report())
        if data is not None and data.get('code') == 0:
            logger.success('Reporter data submitted.')
            return True
        if data is not None:
            logger.warning(f'Reporter submission rejected: {data.get("message", "unknown reason")}')
        return False

    async def start(self) -> None:
        """立即上报并启动定时心跳。"""
        await asyncio.sleep(5)  # 等待t管理器初始化完成
        await self.report()
        self._report_task = asyncio.create_task(self.report_periodically())

    async def report_periodically(self) -> None:
        """定时续期在线状态并同步统计。"""
        while True:
            await asyncio.sleep(REPORT_INTERVAL_SECONDS)
            try:
                await self.report()
            except Exception as error:
                logger.warning(f'Reporter submission failed: {error}')

    async def stop(self) -> bool:
        """停止心跳并通知服务器离线。"""
        if self._report_task is not None:
            self._report_task.cancel()
            self._report_task = None
        data = await post_request(f'{REPORTER_SERVER_URL}/offline.php', {'id': self.machine_id})
        if data is not None and data.get('code') == 0:
            logger.success('Reporter marked offline.')
            return True
        return False


reporter = Reporter()