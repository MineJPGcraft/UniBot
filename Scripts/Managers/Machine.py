"""机器注册管理器：启动时向服务器登记本机，关闭时标记离线。"""

from __future__ import annotations

import hashlib
import socket
import subprocess
import uuid
from pathlib import Path

from Scripts.Logging import logger
from Scripts.Network import post_request

# 机器注册服务器地址
MACHINE_SERVER_URL = 'https://bot-api.mcjpg.dev'


class MachineManager:
    """机器注册管理器，负责生成机器 ID 并与服务器同步在线状态。"""

    machine_id: str = ''
    machine_ip: str = ''

    def init(self) -> None:
        """初始化机器 ID 与 IP，供启动/关闭时上报。"""
        self.machine_id = self.generate_machine_id()
        self.machine_ip = self.get_machine_ip()
        logger.info('Machine identifier initialized.')

    def generate_machine_id(self) -> str:
        """基于固定机器标识生成机器 ID（每次启动重新计算，防止篡改）。"""
        machine_identifier = self.collect_machine_identifier() + ':MC-UniBot'
        return hashlib.sha256(machine_identifier.encode('Utf-8')).hexdigest()

    def collect_machine_identifier(self) -> str:
        """获取稳定的机器主标识（按平台优先级取第一个可用来源）。"""
        # Linux：系统机器 ID（容器内通常由宿主机注入，稳定）
        machine_id_path = Path('/etc/machine-id')
        if machine_id_path.exists():
            machine_id = machine_id_path.read_text('Utf-8').strip()
            if machine_id:
                return machine_id
        # macOS：硬件 UUID
        hardware_uuid = self.get_macos_hardware_uuid()
        if hardware_uuid:
            return hardware_uuid
        # Windows：注册表 MachineGuid
        machine_guid = self.get_windows_machine_guid()
        if machine_guid:
            return machine_guid
        # 跨平台兜底：网卡 MAC 地址
        mac_address = self.get_mac_address()
        if mac_address:
            return mac_address
        # 极端兜底：随机 UUID（仅当所有稳定来源都不可用时）
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
        """读取 macOS 硬件 UUID（IOPlatformUUID）。"""
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

    def get_machine_ip(self) -> str:
        """获取本机对外 IP（通过 UDP 连接探测，不实际发包）。"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(('8.8.8.8', 80))
                return sock.getsockname()[0]
        except Exception:
            return '127.0.0.1'

    async def register(self) -> bool:
        """向服务器登记本机并标记在线，成功返回 True。"""
        url = f'{MACHINE_SERVER_URL}/register.php'
        payload = {'id': self.machine_id, 'ip': self.machine_ip}
        data = await post_request(url, payload)
        if data is None:
            return False
        if data.get('code') == 0:
            logger.success('Machine registered and marked online.')
            return True
        logger.warning(f'Machine registration rejected: {data.get("message", "unknown reason")}')
        return False

    async def mark_offline(self) -> bool:
        """通知服务器本机离线，成功返回 True。"""
        url = f'{MACHINE_SERVER_URL}/offline.php'
        payload = {'id': self.machine_id}
        data = await post_request(url, payload)
        if data is None:
            return False
        if data.get('code') == 0:
            logger.success('Machine marked offline.')
            return True
        logger.warning(f'Failed to mark machine offline: {data.get("message", "unknown reason")}')
        return False


machine_manager = MachineManager()
