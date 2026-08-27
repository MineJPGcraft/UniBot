"""通用工具函数测试。"""

from Scripts.Utils import flatten_minecraft_motd, strip_minecraft_color


class TestStripMinecraftColor:
    def test_single_color_codes(self):
        assert strip_minecraft_color('§6已运行时间：§c7 小时') == '已运行时间：7 小时'

    def test_uppercase_codes(self):
        assert strip_minecraft_color('§A测试§B文本') == '测试文本'

    def test_format_codes(self):
        assert strip_minecraft_color('§l加粗§o斜体§r重置') == '加粗斜体重置'

    def test_hex_color_sequence(self):
        assert strip_minecraft_color('§x§1§2§3§4§5§6测试') == '测试'

    def test_plain_text_unchanged(self):
        assert strip_minecraft_color('没有颜色的文本') == '没有颜色的文本'

    def test_empty_string(self):
        assert strip_minecraft_color('') == ''

class TestFlattenMinecraftMotd:
    def test_plain_string(self):
        assert flatten_minecraft_motd('A Minecraft Server') == 'A Minecraft Server'

    def test_json_component_with_extra(self):
        description = {'text': 'Hello ', 'extra': [{'text': 'World', 'color': 'red'}]}
        assert flatten_minecraft_motd(description) == 'Hello World'

    def test_nested_component_array(self):
        description = [
            {'text': '✦ ', 'color': 'yellow'},
            {'text': 'NowaDream', 'color': 'red'},
            ' | ',
            {'text': '⛏ 纯净生存', 'color': 'green'},
        ]
        assert flatten_minecraft_motd(description) == '✦ NowaDream | ⛏ 纯净生存'

    def test_legacy_color_codes_stripped(self):
        assert flatten_minecraft_motd('§a在线 §7玩家') == '在线 玩家'

    def test_multiline_collapsed_to_single_line(self):
        description = {'text': '第一行\n第二行', 'extra': [{'text': ' 尾部'}]}
        assert flatten_minecraft_motd(description) == '第一行 第二行 尾部'

    def test_translate_component(self):
        description = {'translate': 'multiplayer.player.joined', 'with': [{'text': 'Steve'}]}
        assert flatten_minecraft_motd(description) == 'multiplayer.player.joinedSteve'

    def test_none_and_empty(self):
        assert flatten_minecraft_motd(None) == ''
        assert flatten_minecraft_motd('') == ''
        assert flatten_minecraft_motd({}) == ''
