import uuid
from asyncio import Lock
from datetime import UTC, datetime
from json import dumps, loads
from pathlib import Path

import bcrypt

from Scripts.Logging import logger


class DataManager:
    """数据管理器，负责 WebUI 用户的 CRUD 及密码哈希。"""

    users: dict[str, dict] = {}

    data_dir = Path('Data')

    users_file = data_dir / 'Users.json'
    secret_file = data_dir / 'Secret.key'

    lock = Lock()

    def load(self):
        """加载 WebUI 用户数据与 JWT 密钥。"""
        if not self.data_dir.exists():
            logger.warning('Data directory does not exist, creating it...')
            self.data_dir.mkdir(parents=True, exist_ok=True)
        # 加载 WebUI 用户数据
        if self.users_file.exists():
            try:
                self.users = loads(self.users_file.read_text('Utf-8'))
            except Exception:
                logger.warning('User data file is corrupted, falling back to empty data.')
                self.users = {}
        # 生成或加载 JWT 签名密钥
        self.secret_key = self.load_secret_key()
        logger.success('Data files loaded successfully.')

    def load_secret_key(self) -> str:
        """生成或加载 JWT 签名密钥。"""
        if self.secret_file.exists():
            return self.secret_file.read_text('Utf-8').strip()
        secret_key = uuid.uuid4().hex + uuid.uuid4().hex
        self.secret_file.write_text(secret_key, encoding='Utf-8')
        return secret_key

    async def save(self):
        """持久化 WebUI 用户数据。"""
        async with self.lock:
            self.users_file.write_text(dumps(self.users, ensure_ascii=False, indent=2), encoding='Utf-8')
            logger.success('Data files saved successfully.')

    # ── WebUI 用户管理 ────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        """是否已有用户（已初始化）。"""
        return len(self.users) > 0

    def hash_password(self, password: str) -> str:
        """使用 bcrypt 哈希密码。"""
        return bcrypt.hashpw(password.encode('Utf-8'), bcrypt.gensalt()).decode('Utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码。"""
        return bcrypt.checkpw(password.encode('Utf-8'), hashed.encode('Utf-8'))

    async def create_user(self, username: str, password: str, nickname: str, role: str = 'viewer') -> dict | None:
        """创建用户，返回用户信息（不含密码哈希）。"""
        if self.get_user_by_username(username):
            return None
        user_id = f'u_{uuid.uuid4().hex[:12]}'
        now = datetime.now(UTC).isoformat()
        user_data = {
            'user_id': user_id,
            'username': username,
            'nickname': nickname,
            'role': role,
            'password_hash': self.hash_password(password),
            'created_at': now,
            'last_login_at': None,
        }
        self.users[user_id] = user_data
        await self.save()
        return self.public_user_info(user_data)

    def get_user_by_username(self, username: str) -> dict | None:
        """通过用户名查找用户。"""
        for user_data in self.users.values():
            if user_data['username'] == username:
                return user_data
        return None

    def get_user_by_id(self, user_id: str) -> dict | None:
        """通过 user_id 查找用户。"""
        return self.users.get(user_id)

    def public_user_info(self, user_data: dict) -> dict:
        """返回不含密码哈希的用户信息。"""
        return {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'nickname': user_data['nickname'],
            'role': user_data['role'],
            'created_at': user_data['created_at'],
            'last_login_at': user_data.get('last_login_at'),
        }

    async def update_last_login(self, user_id: str):
        """更新最后登录时间。"""
        if user_data := self.users.get(user_id):
            user_data['last_login_at'] = datetime.now(UTC).isoformat()
            await self.save()

    async def update_user(self, user_id: str, nickname: str | None = None, role: str | None = None) -> bool:
        """更新用户昵称或角色。"""
        user_data = self.users.get(user_id)
        if not user_data:
            return False
        if nickname is not None:
            user_data['nickname'] = nickname
        if role is not None:
            user_data['role'] = role
        await self.save()
        return True

    async def reset_password(self, user_id: str, password: str) -> bool:
        """重置用户密码。"""
        user_data = self.users.get(user_id)
        if not user_data:
            return False
        user_data['password_hash'] = self.hash_password(password)
        await self.save()
        return True

    async def delete_user(self, user_id: str) -> bool:
        """删除用户。"""
        if user_id not in self.users:
            return False
        self.users.pop(user_id)
        await self.save()
        return True


data_manager = DataManager()
