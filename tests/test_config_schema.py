"""配置表单 Schema 契约测试。

`Scripts/Api/Config/Schema.py` 统一输出标准 JSON Schema，前端按同一套规则渲染
Config.toml / .env / 扩展配置三类表单。本测试锁定该契约，避免结构回退为自定义
字段列表（`fields` / `type: 'list'` 等旧形态）。
"""

from Scripts.Api.Config.Schema import (
    build_config_groups,
    build_config_schema,
    build_env_groups,
    build_env_schema,
)


def _property_keys(schema: dict) -> set[str]:
    return set(schema['properties'])


class TestConfigSchema:
    def test_root_is_json_schema_object(self):
        schema = build_config_schema()
        assert schema['type'] == 'object'
        assert isinstance(schema['properties'], dict)

    def test_every_group_key_is_declared(self):
        """分组引用的 key 必须都在 properties 中声明，否则前端渲染为空。"""
        properties = _property_keys(build_config_schema())
        for group in build_config_groups():
            assert set(group['keys']) <= properties, group['id']

    def test_every_property_belongs_to_a_group(self):
        grouped = {key for group in build_config_groups() for key in group['keys']}
        assert _property_keys(build_config_schema()) == grouped

    def test_platform_lists_use_items_format(self):
        """平台列表以 `items.format: 'platform'` 表达，选项走 x-options。"""
        properties = build_config_schema()['properties']
        for key in ('command_groups', 'message_groups'):
            field = properties[key]
            assert field['type'] == 'array'
            assert field['items'] == {'type': 'string', 'format': 'platform'}
            assert field['x-options']

    def test_nested_keys_are_flat_property_names(self):
        """Config.toml 的嵌套配置以点号平铺为字段名。"""
        properties = _property_keys(build_config_schema())
        assert {'image.mode', 'webui.enabled'} <= properties

    def test_every_field_has_title(self):
        for key, field in build_config_schema()['properties'].items():
            assert field.get('title'), key

    def test_schema_is_rebuilt_per_call(self):
        """每次调用返回全新结构，避免调用方改动污染后续请求。"""
        first = build_config_schema()
        first['properties']['bot_prefix']['title'] = 'mutated'
        assert build_config_schema()['properties']['bot_prefix']['title'] != 'mutated'


class TestEnvSchema:
    def test_root_is_json_schema_object(self):
        schema = build_env_schema()
        assert schema['type'] == 'object'
        assert isinstance(schema['properties'], dict)

    def test_object_arrays_reference_definitions(self):
        """机器人列表以 `$ref` 指向 `$defs`，前端据此渲染卡片列表。"""
        schema = build_env_schema()
        definitions = schema['$defs']
        for key in ('QQ_BOTS', 'TELEGRAM_BOTS', 'DISCORD_BOTS', 'DODO_BOTS', 'KAIHEILA_BOTS'):
            ref = schema['properties'][key]['items']['$ref']
            assert ref.startswith('#/$defs/')
            assert ref.rsplit('/', 1)[-1] in definitions

    def test_every_ref_resolves(self):
        schema = build_env_schema()

        def collect_refs(node):
            if isinstance(node, dict):
                for name, child in node.items():
                    if name == '$ref':
                        yield child
                    else:
                        yield from collect_refs(child)
            elif isinstance(node, list):
                for child in node:
                    yield from collect_refs(child)

        for ref in collect_refs(schema):
            assert ref.rsplit('/', 1)[-1] in schema['$defs'], ref

    def test_secrets_use_password_format(self):
        properties = build_env_schema()['properties']
        for key in ('ONEBOT_ACCESS_TOKEN', 'MINECRAFT_ACCESS_TOKEN'):
            assert properties[key]['format'] == 'password'

    def test_key_value_map_uses_additional_properties(self):
        field = build_env_schema()['properties']['MINECRAFT_WS_URLS']
        assert field['type'] == 'object'
        assert field['additionalProperties'] == {'type': 'array', 'items': {'type': 'string'}}

    def test_every_group_key_is_declared(self):
        properties = _property_keys(build_env_schema())
        for group in build_env_groups():
            assert set(group['keys']) <= properties, group['id']

    def test_every_property_belongs_to_a_group(self):
        grouped = {key for group in build_env_groups() for key in group['keys']}
        assert _property_keys(build_env_schema()) == grouped

    def test_every_field_has_title(self):
        for key, field in build_env_schema()['properties'].items():
            assert field.get('title'), key
