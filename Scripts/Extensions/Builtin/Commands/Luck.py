"""内置扩展：今日人品指令。"""

import random
from datetime import date
from hashlib import md5
from typing import override

from nonebot_plugin_uninfo import Uninfo

from Scripts import Globals
from Scripts.Extensions import Command, Extension, SubCommand
from Scripts.Messages import messages
from Scripts.Utils import turn_message_text

# 创建唯一扩展实例，能力经实例装饰器登记
extension = Extension(id='Luck', name=messages.builtin_extensions.luck, version='1.0.1', types=('command',))

# 内存中的今日运势排行：桶结构，索引即人品值（10-100），每桶存该分值的用户记录，跨天自动清空
luck_rank: list[list[dict[str, str | int]]] = [[] for _ in range(101)]
luck_rank_date: date | None = None


def record_luck(user_id: str, user_name: str, luck_point: int) -> None:
    """记录用户今日人品到内存排行，跨天自动刷新；已记录过的用户不重复记录。"""
    global luck_rank_date

    today = date.today()
    if luck_rank_date != today:
        for bucket in luck_rank:
            bucket.clear()
        luck_rank_date = today
    for bucket in luck_rank:
        for record in bucket:
            if record['user_id'] == user_id:
                return
    luck_rank[luck_point].append({'user_id': user_id, 'name': user_name, 'point': luck_point})


@extension.register_command
class LuckCommand(Command):
    """查看今日人品值。"""

    name = 'luck'
    description = messages.commands.luck.description
    usage = messages.commands.luck.usage

    @override
    async def handler(self, session: Uninfo):
        luck_data = self.get_luck_data(session)
        return await turn_message_text(self.luck_handler(luck_data))

    @override
    async def image_handler(self, session: Uninfo) -> bytes:
        """渲染今日人品为图片，返回 PNG 字节（由框架在图像模式发送）。"""
        luck_data = self.get_luck_data(session)
        return await extension.render_image('Luck', (500, 0), context=luck_data)

    def get_luck_data(self, session: Uninfo) -> dict:
        bad_things = messages.commands.luck.bad_things
        good_things = messages.commands.luck.good_things
        user_id = str(session.user.id)
        scene_id = str(session.scene.id)
        seed_hash = md5(f'{date.today()} {scene_id} {user_id}'.encode())
        random.seed(seed := int(seed_hash.hexdigest(), 16))
        luck_point = random.randint(10, 100)
        # 查询即记录排行：已绑定用户显示绑定玩家名，未绑定用户显示昵称
        bound_players = Globals.player_service.players.get(user_id, []) if Globals.player_service else []
        record_luck(user_id, bound_players[0] if bound_players else session.user.name or user_id, luck_point)
        tips = messages.commands.luck.tip_low
        if luck_point > 90:
            tips = messages.commands.luck.tip_max
        elif luck_point > 60:
            tips = messages.commands.luck.tip_high
        elif luck_point > 30:
            tips = messages.commands.luck.tip_mid
        scene_index = int(scene_id.replace('-', '0'), 32)
        bad_thing = bad_things[(seed & scene_index) % len(bad_things)]
        good_thing = good_things[(seed ^ scene_index) % len(good_things)]
        if bad_thing.startswith(good_thing[:2]):
            bad_thing = bad_things[bad_things.index(bad_thing) - 1]
        return {
            'luck_point': luck_point,
            'tips': tips,
            'good_thing': good_thing,
            'bad_thing': bad_thing,
        }

    def luck_handler(self, data: dict):
        yield messages.commands.luck.result.format(point=data['luck_point'], tips=data['tips'])
        yield messages.commands.luck.good.format(thing=data['good_thing'])
        yield messages.commands.luck.bad.format(thing=data['bad_thing'])

    class Rank(SubCommand['LuckCommand']):
        """查看今日运势排行。"""

        name = 'rank'
        description = messages.commands.luck.rank_desc

        @override
        async def handler(self, session: Uninfo):
            # 查询排行时也记录当前用户今日人品
            self.parent.get_luck_data(session)
            return await turn_message_text(self.rank_handler())

        @override
        async def image_handler(self, session: Uninfo) -> bytes:
            """渲染今日运势排行图片，返回 PNG 字节（由框架在图像模式发送）。"""
            # 查询排行时也记录当前用户今日人品
            self.parent.get_luck_data(session)
            return await extension.render_image('Luck/Rank', (500, 0), context={'rank': self.get_rank_data()})

        def get_rank_data(self) -> list[dict[str, str | int]]:
            """返回今日运势排行数据（按人品值从高到低）。"""
            rank = []
            index = 0
            for point in range(100, 9, -1):
                for record in luck_rank[point]:
                    index += 1
                    rank.append({'index': index, 'name': record['name'], 'point': record['point']})
            return rank

        def rank_handler(self):
            if not any(luck_rank):
                yield messages.commands.luck.rank_empty
                return
            yield messages.commands.luck.rank_title
            for record in self.get_rank_data():
                yield messages.commands.luck.rank_line.format(
                    index=record['index'], name=record['name'], point=record['point']
                )
